import sys
import os
import numpy as np
import torch
import torch.multiprocessing
from torch.utils.data import DataLoader
import torch.nn as nn
import torch.optim as optim
from models.deeplab import DeepLab
from sklearn.metrics import jaccard_score
from sklearn.metrics import confusion_matrix
from models.coral_dataset import CoralsDataset
import models.losses as losses
from PyQt5.QtWidgets import QApplication

# SEED
torch.manual_seed(997)
np.random.seed(997)
torch.backends.cudnn.deterministic = True
torch.backends.cudnn.benchmark = False


def checkDataset(dataset_folder):
    """
    Check if the training, validation and test folders exist and contain the corresponding images and labels.
    """

    flag = 0
    targetdirs = ["training", "validation", "test"]
    if os.path.exists(dataset_folder):
        for sub in targetdirs:
            subfolder = os.path.join(dataset_folder, sub)
            if os.path.exists(subfolder):
                if os.listdir(subfolder) == ['images', 'labels'] and len(set(os.listdir(os.path.join(subfolder, os.listdir(subfolder)[0]))) - set(os.listdir(os.path.join(subfolder, os.listdir(subfolder)[1]))))==0:
                    flag = 0 # Your training dataset is valid
                else:
                    return 3  # Files mismatch in subfolder
            else:
                return 2  # A subfolder is missing
    else:
        return 1  # Dataset folder does not exist

    return flag

def createTargetClasses(annotations):
    """
    Create the label name - label code correspondences for the classifier.
    """

    labels_set = set()

    # Background class must be present
    labels_set.add("Background")

    for blob in annotations.seg_blobs:
        if blob.qpath_gitem.isVisible():
            labels_set.add(blob.class_name)

    target_dict = {}
    for i, label in enumerate(labels_set):
        target_dict[label] = i

    return target_dict


def saveMetrics(metrics, filename):
    """
    Save the computed metrics.
    """

    file = open(filename, 'w')
    file.write("CONFUSION MATRIX: \n\n")
    np.savetxt(file, metrics['ConfMatrix'], fmt='%d')
    file.write("\n")
    file.write("NORMALIZED CONFUSION MATRIX: \n\n")
    np.savetxt(file, metrics['NormConfMatrix'], fmt='%.3f')
    file.write("\n")
    file.write("ACCURACY      : %.3f\n\n" % metrics['Accuracy'])
    file.write("Jaccard Score : %.3f\n\n" % metrics['JaccardScore'])
    file.close()


# VALIDATION
def evaluateNetwork(dataset, dataloader, loss_to_use, CEloss, w_for_GDL, tversky_loss_alpha, tversky_loss_beta,
                    focal_tversky_gamma, epoch, epochs_switch, epochs_transition, nclasses, net,
                    progress, flag_compute_mIoU=False, flag_test=False, savefolder=""):
    """
    It evaluates the network on the validation set.  
    :param dataloader: Pytorch DataLoader to load the dataset for the evaluation.
    :param net: Network to evaluate.
    :param savefolder: if a folder is given the classification results are saved into this folder. 
    :return: all the computed metrics.
    """""

    ##### SETUP THE NETWORK #####

    USE_CUDA = torch.cuda.is_available()

    if USE_CUDA:
        device = torch.device("cuda")
        net.to(device)
        torch.cuda.synchronize()

    ##### EVALUATION #####

    net.eval()  # set the network in evaluation mode

    batch_size = dataloader.batch_size

    CM = np.zeros((nclasses, nclasses), dtype=int)
    class_indices = list(range(nclasses))

    num_iter = 0
    total_iter = int(len(dataset) / dataloader.batch_size)

    ypred_list = []
    ytrue_list = []
    loss_values_per_iter = []
    with torch.no_grad():
        for k, data in enumerate(dataloader):

            batch_images, labels_batch, names = data['image'], data['labels'], data['name']
            print(names)

            if USE_CUDA:
                batch_images = batch_images.to(device)
                labels_batch = labels_batch.to(device)

            # N x K x H x W --> N: batch size, K: number of classes, H: height, W: width
            outputs = net(batch_images)

            # predictions size --> N x H x W
            values, predictions_t = torch.max(outputs, 1)

            if loss_to_use == "NONE":
                loss_values_per_iter.append(0.0)
            else:
                loss = computeLoss(loss_to_use, CEloss, w_for_GDL, tversky_loss_alpha, tversky_loss_beta,
                                   focal_tversky_gamma, epoch, epochs_switch, epochs_transition, labels_batch, outputs)

                loss_values_per_iter.append(loss.item())

            pred_cpu = predictions_t.cpu()
            labels_cpu = labels_batch.cpu()

            if flag_compute_mIoU:
                ypred_list.extend(pred_cpu.numpy().ravel())
                ytrue_list.extend(labels_cpu.numpy().ravel())

            # CONFUSION MATRIX, PREDICTIONS ARE PER-COLUMN, GROUND TRUTH CLASSES ARE PER-ROW
            for i in range(batch_size):
                pred_index = pred_cpu[i].numpy().ravel()
                true_index = labels_cpu[i].numpy().ravel()
                confmat = confusion_matrix(true_index, pred_index, labels=class_indices)
                CM += confmat

            if flag_test is True:
                updateProgressBar(progress, "Test - Iteration ", num_iter, total_iter)
            else:
                updateProgressBar(progress, "Validation - Iteration ", num_iter, total_iter)

            num_iter = num_iter + 1

            # SAVE THE OUTPUT OF THE NETWORK
            for i in range(batch_size):

                if savefolder:
                    imgfilename = os.path.join(savefolder, names[i])
                    dataset.saveClassificationResult(batch_images[i].cpu(), outputs[i].cpu(), imgfilename)

    jaccard_s = 0.0

    if flag_compute_mIoU:
        ypred = np.array(ypred_list)
        del ypred_list
        ytrue = np.array(ytrue_list)
        del ytrue_list
        jaccard_s = jaccard_score(ytrue, ypred, average='weighted')

    # NORMALIZED CONFUSION MATRIX
    sum_row = CM.sum(axis=1)
    sum_row = sum_row.reshape((nclasses, 1))   # transform into column vector
    sum_row = sum_row + 1
    CMnorm = CM / sum_row    # divide each row using broadcasting


    # FINAL ACCURACY
    pixels_total = CM.sum()
    pixels_correct = np.sum(np.diag(CM))
    accuracy = float(pixels_correct) / float(pixels_total)

    metrics = {'ConfMatrix': CM, 'NormConfMatrix': CMnorm, 'Accuracy': accuracy, 'JaccardScore': jaccard_s}

    mean_loss = sum(loss_values_per_iter) / len(loss_values_per_iter)

    return metrics, mean_loss


def computeLoss(loss_name, CE, w_for_GDL, tversky_alpha, tversky_beta, focal_tversky_gamma,
                epoch, epochs_switch, epochs_transition, labels, predictions):
    """
    Compute the loss given its name.
    """

    if loss_name == "CROSSENTROPY":
        loss = CE(predictions, labels)
    elif loss_name == "DICE":
        loss = losses.GDL(predictions, labels, w_for_GDL)
    elif loss_name == "BOUNDARY":
        loss = losses.surface_loss(labels, predictions)
    elif loss_name == "DICE+BOUNDARY":
        if epoch >= epochs_switch:
            alpha = 1.0 - (float(epoch - epochs_switch) / float(epochs_transition))
            if alpha < 0.0:
                alpha = 0.0
            GDL = losses.GDL(predictions, labels, w_for_GDL)
            B = losses.surface_loss(labels, predictions)
            loss = alpha * GDL + (1.0 - alpha) * B

            str = "Alpha={:.4f}, GDL={:.4f}, Boundary={:.4f}, loss={:.4f}".format(alpha, GDL, B, loss)
            print(str)
        else:
            loss = losses.GDL(predictions, labels, w_for_GDL)
    elif loss_name == "FOCAL_TVERSKY":
        loss = losses.focal_tversky(predictions, labels, tversky_alpha, tversky_beta, focal_tversky_gamma)
    elif loss_name == "FOCAL+BOUNDARY":
        if epoch >= epochs_switch:
            alpha = 1.0 - (float(epoch - epochs_switch) / float(epochs_transition))
            if alpha < 0.0:
                alpha = 0.0
            loss = alpha * losses.focal_tversky(predictions, labels, tversky_alpha, tversky_beta,
                                                focal_tversky_gamma) + (1.0 - alpha) * losses.surface_loss(labels, predictions)
        else:
            loss = losses.focal_tversky(predictions, labels, tversky_alpha, tversky_beta, focal_tversky_gamma)

    return loss


def updateProgressBar(progress_bar, prefix_message, num_iter, total_iter):
    """
    Update progress bar according to the number of iterations done.
    """

    txt = prefix_message + str(num_iter + 1) + "/" + str(total_iter)
    progress_bar.setMessage(txt)
    perc_training = round((100.0 * num_iter) / total_iter)
    progress_bar.setProgress(perc_training)
    QApplication.processEvents()


def trainingNetwork(images_folder_train, labels_folder_train, images_folder_val, labels_folder_val,
                    labels_dictionary, target_classes, output_classes, save_network_as, classifier_name,
                    epochs, batch_sz, batch_mult, learning_rate, L2_penalty, validation_frequency, loss_to_use,
                    epochs_switch, epochs_transition, tversky_alpha, tversky_gamma, optimiz,
                    flag_shuffle, flag_training_accuracy, progress):

    ##### DATA #####

    # setup the training dataset
    datasetTrain = CoralsDataset(images_folder_train, labels_folder_train, labels_dictionary, target_classes)

    print("Dataset setup..", end='')
    datasetTrain.computeAverage()
    datasetTrain.computeWeights()
    print(datasetTrain.dict_target)
    print(datasetTrain.weights)
    freq = 1.0 / datasetTrain.weights
    print(freq)
    print("done.")

    save_classifier_as = save_network_as.replace(".net", ".json")

    datasetTrain.enableAugumentation()

    datasetVal = CoralsDataset(images_folder_val, labels_folder_val, labels_dictionary, datasetTrain.dict_target)
    datasetVal.dataset_average = datasetTrain.dataset_average
    datasetVal.weights = datasetTrain.weights

    #AUGUMENTATION IS NOT APPLIED ON THE VALIDATION SET
    datasetVal.disableAugumentation()

    # setup the data loader
    dataloaderTrain = DataLoader(datasetTrain, batch_size=batch_sz, shuffle=flag_shuffle, num_workers=0, drop_last=True,
                                 pin_memory=True)

    validation_batch_size = 4
    dataloaderVal = DataLoader(datasetVal, batch_size=validation_batch_size, shuffle=False, num_workers=0, drop_last=True,
                                 pin_memory=True)

    training_images_number = len(datasetTrain.images_names)
    validation_images_number = len(datasetVal.images_names)

    print("NETWORK USED: DEEPLAB V3+")

    ###### SETUP THE NETWORK #####
    net = DeepLab(backbone='resnet', output_stride=16, num_classes=output_classes)
    state = torch.load("models/deeplab-resnet.pth.tar")
    # RE-INIZIALIZE THE CLASSIFICATION LAYER WITH THE RIGHT NUMBER OF CLASSES, DON'T LOAD WEIGHTS OF THE CLASSIFICATION LAYER
    new_dictionary = state['state_dict']
    del new_dictionary['decoder.last_conv.8.weight']
    del new_dictionary['decoder.last_conv.8.bias']
    net.load_state_dict(state['state_dict'], strict=False)

    # OPTIMIZER
    if optimiz == "SGD":
        optimizer = optim.SGD(net.parameters(), lr=learning_rate, weight_decay=L2_penalty, momentum=0.9)
    elif optimiz == "ADAM":
        optimizer = optim.Adam(net.parameters(), lr=learning_rate, weight_decay=L2_penalty)

    USE_CUDA = torch.cuda.is_available()

    if USE_CUDA:
        device = torch.device("cuda")
    else:
        device = torch.device("cpu")

    net.to(device)

    ##### TRAINING LOOP #####

    reduce_lr_patience = 2
    if loss_to_use == "DICE+BOUNDARY":
        reduce_lr_patience = 200
        print("patience increased !")

    scheduler = optim.lr_scheduler.ReduceLROnPlateau(optimizer, patience=reduce_lr_patience, verbose=True)

    best_accuracy = 0.0
    best_jaccard_score = 0.0

    # Crossentropy loss
    weights = datasetTrain.weights
    class_weights = torch.FloatTensor(weights).cuda()
    CEloss = nn.CrossEntropyLoss(weight=class_weights, ignore_index=-1)

    # weights for GENERALIZED DICE LOSS (GDL)
    freq = 1.0 / datasetTrain.weights[1:]
    w = 1.0 / (freq * freq)
    w = w / w.sum() + 0.00001
    w_for_GDL = torch.from_numpy(w)
    w_for_GDL = w_for_GDL.to(device)

    # Focal Tversky loss
    focal_tversky_gamma = torch.tensor(tversky_gamma)
    focal_tversky_gamma = focal_tversky_gamma.to(device)

    tversky_loss_alpha = torch.tensor(tversky_alpha)
    tversky_loss_beta = torch.tensor(1.0 - tversky_alpha)
    tversky_loss_alpha = tversky_loss_alpha.to(device)
    tversky_loss_beta = tversky_loss_beta.to(device)



    print("Training Network")
    num_iter = 0
    total_iter = epochs * int(len(datasetTrain) / dataloaderTrain.batch_size)

    # mean loss value per-epoch
    loss_values_train = []
    loss_values_val = []

    for epoch in range(epochs):

        net.train()
        optimizer.zero_grad()

        loss_values_per_iter = []
        for i, minibatch in enumerate(dataloaderTrain):

            updateProgressBar(progress, "Training - Iteration ", num_iter, total_iter)
            num_iter += 1

            # get the inputs
            images_batch = minibatch['image']
            labels_batch = minibatch['labels']

            if USE_CUDA:
                images_batch = images_batch.to(device)
                labels_batch = labels_batch.to(device)

            # forward+loss+backward
            outputs = net(images_batch)

            loss = computeLoss(loss_to_use, CEloss, w_for_GDL, tversky_loss_alpha, tversky_loss_beta, focal_tversky_gamma,
                               epoch, epochs_switch, epochs_transition, labels_batch, outputs)

            loss.backward()

            # TO AVOID MEMORY TROUBLE UPDATE WEIGHTS EVERY BATCH SIZE x BATCH MULT
            if (i+1)% batch_mult == 0:
                optimizer.step()
                optimizer.zero_grad()

            print(epoch, i, loss.item())
            loss_values_per_iter.append(loss.item())

        mean_loss_train = sum(loss_values_per_iter) / len(loss_values_per_iter)
        print("Epoch: %d , Mean loss = %f" % (epoch, mean_loss_train))

        loss_values_train.append(mean_loss_train)

        ### VALIDATION ###
        if epoch > 0 and (epoch+1) % validation_frequency == 0:

            print("RUNNING VALIDATION.. ", end='')

            metrics_val, mean_loss_val = evaluateNetwork(datasetVal, dataloaderVal, loss_to_use, CEloss, w_for_GDL,
                                                         tversky_loss_alpha, tversky_loss_beta, focal_tversky_gamma,
                                                         epoch, epochs_switch, epochs_transition,
                                                         output_classes, net, progress, flag_compute_mIoU=False,
                                                         flag_test=False)
            accuracy = metrics_val['Accuracy']
            jaccard_score = metrics_val['JaccardScore']
            scheduler.step(mean_loss_val)
            loss_values_val.append(mean_loss_val)

            accuracy_training = 0.0
            jaccard_training = 0.0

            if flag_training_accuracy is True:
                metrics_train, mean_loss_train = evaluateNetwork(datasetTrain, dataloaderTrain, loss_to_use, CEloss, w_for_GDL,
                                                                 tversky_loss_alpha, tversky_loss_beta, focal_tversky_gamma,
                                                                 epoch, epochs_switch, epochs_transition,
                                                                 output_classes, net, progress,
                                                                 flag_compute_mIoU=False, flag_test=False)
                accuracy_training = metrics_train['Accuracy']
                jaccard_training = metrics_train['JaccardScore']

            #if jaccard_score > best_jaccard_score:
            if accuracy > best_accuracy:
                best_accuracy = accuracy
                best_jaccard_score = jaccard_score
                torch.save(net.state_dict(), save_network_as)
                # performance of the best accuracy network on the validation dataset
                metrics_filename = save_network_as[:len(save_network_as) - 4] + "-val-metrics.txt"
                saveMetrics(metrics_val, metrics_filename)


            print("-> CURRENT BEST ACCURACY ", best_accuracy)

            # restore training messages
            updateProgressBar(progress, "Training - Iteration ", num_iter, total_iter)

    # main loop ended
    torch.cuda.empty_cache()
    del net
    net = None

    print("***** TRAINING FINISHED *****")
    print("BEST ACCURACY REACHED ON THE VALIDATION SET: %.3f " % best_accuracy)

    return datasetTrain, loss_values_train, loss_values_val


def testNetwork(images_folder, labels_folder, labels_dictionary, target_classes, dataset_train,
                network_filename, output_folder, progress):
    """
    Load a network and test it on the test dataset.
    :param network_filename: Full name of the network to load (PATH+name)
    """

    # TEST DATASET
    datasetTest = CoralsDataset(images_folder, labels_folder, labels_dictionary, target_classes)
    datasetTest.disableAugumentation()

    datasetTest.num_classes = dataset_train.num_classes
    datasetTest.weights = dataset_train.weights
    datasetTest.dataset_average = dataset_train.dataset_average
    datasetTest.dict_target = dataset_train.dict_target

    output_classes = dataset_train.num_classes

    batchSize = 4
    dataloaderTest = DataLoader(datasetTest, batch_size=batchSize, shuffle=False, num_workers=0, drop_last=True,
                            pin_memory=True)

    # DEEPLAB V3+
    net = DeepLab(backbone='resnet', output_stride=16, num_classes=output_classes)
    net.load_state_dict(torch.load(network_filename))
    print("Weights loaded.")

    metrics_test, loss = evaluateNetwork(datasetTest, dataloaderTest, "NONE", None, [0.0], 0.0, 0.0, 0.0, 0, 0, 0,
                                         output_classes, net, progress, True, True, output_folder)
    metrics_filename = network_filename[:len(network_filename) - 4] + "-test-metrics.txt"
    saveMetrics(metrics_test, metrics_filename)
    print("***** TEST FINISHED *****")

    return metrics_test
