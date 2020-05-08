# -*- coding: utf-8 -*-

import os
import pickle
import numpy as np
import torch
import torch.multiprocessing
from torch.utils.data import DataLoader
import matplotlib.pyplot as plt
import torch.nn as nn
import torch.optim as optim
from sklearn.metrics import jaccard_score
from sklearn.metrics import confusion_matrix
from models.deeplab import DeepLab
from models.coral_dataset import CoralsDataset

import time
import json


# SEED
torch.manual_seed(997)
np.random.seed(997)
torch.backends.cudnn.deterministic = True
torch.backends.cudnn.benchmark = False


def checkDataset(dataset_folder):

    """
    Check if the training, validation and test folders exist and contain the corresponding images and labels.
    """

    pass

def createTargetClasses(annotations):
    """
    Create the label name - label code correspondences for the classifier.
    """
    pass


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
def evaluateNetwork(dataloader, weights, nclasses, net, flagTrainingDataset=False, savefolder=""):
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


    class_weights = torch.FloatTensor(weights).cuda()
    lossfn = nn.CrossEntropyLoss(weight=class_weights, ignore_index=-1)
    batch_size = dataloader.batch_size

    CM = np.zeros((nclasses, nclasses), dtype=int)
    class_indices = list(range(nclasses))

    ypred_list = []
    ytrue_list = []
    loss_values = []
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

            loss = lossfn(outputs, labels_batch)
            loss_values.append(loss)

            pred_cpu = predictions_t.cpu()
            labels_cpu = labels_batch.cpu()

            if not flagTrainingDataset:
                ypred_list.extend(pred_cpu.numpy().ravel())
                ytrue_list.extend(labels_cpu.numpy().ravel())

            # CONFUSION MATRIX, PREDICTIONS ARE PER-COLUMN, GROUND TRUTH CLASSES ARE PER-ROW
            for i in range(batch_size):
                print(i)
                pred_index = pred_cpu[i].numpy().ravel()
                true_index = labels_cpu[i].numpy().ravel()
                confmat = confusion_matrix(true_index, pred_index, class_indices)
                CM += confmat

            # SAVE THE OUTPUT OF THE NETWORK
            for i in range(batch_size):

                if savefolder:
                    imgfilename = os.path.join(savefolder, names[i])
                    CoralsDataset.saveClassificationResult(batch_images[i].cpu(), outputs[i].cpu(), imgfilename)

    mean_loss = sum(loss_values) / len(loss_values)

    jaccard_s = 0.0

    if not flagTrainingDataset:
        ypred = np.array(ypred_list)
        del ypred_list
        ytrue = np.array(ytrue_list)
        del ytrue_list
        jaccard_s = jaccard_score(ytrue, ypred, average='weighted')

    # NORMALIZED CONFUSION MATRIX
    sum_row = CM.sum(axis=1)
    sum_row = sum_row.reshape((nclasses, 1))   # transform into column vector
    CMnorm = CM / sum_row    # divide each row using broadcasting


    # FINAL ACCURACY
    pixels_total = CM.sum()
    pixels_correct = np.sum(np.diag(CM))
    accuracy = float(pixels_correct) / float(pixels_total)


    metrics = {'ConfMatrix': CM, 'NormConfMatrix': CMnorm, 'Accuracy': accuracy, 'JaccardScore': jaccard_s}

    return metrics, mean_loss


def updateAvailableClassifiers(current_classifiers, classifier_name, dataset):

    dict = {}

    dict["Classifier Name"] = classifier_name
    dict["Weights"] = list(dataset.weights)
    dict["Average"] = list(dataset.dataset_average)
    dict["Num. Classes"] = dataset.num_classes
    dict["Classes"] = dataset.dict_target


def trainingNetwork(images_folder_train, labels_folder_train, images_folder_val, labels_folder_val,
                    dictionary, target_classes, num_classes, save_network_as, current_classifiers, classifier_name,
                    epochs, batch_sz, batch_mult, learning_rate, L2_penalty, validation_frequency, flagShuffle, experiment_name):

    ##### DATA #####

    # setup the training dataset
    datasetTrain = CoralsDataset(images_folder_train, labels_folder_train, dictionary, target_classes, num_classes)

    print("Dataset setup..", end='')
    datasetTrain.computeAverage()
    datasetTrain.computeWeights()
    print("done.")

    updateAvailableClassifiers(current_classifiers, classifier_name, datasetTrain)

    datasetTrain.enableAugumentation()

    datasetVal = CoralsDataset(images_folder_val, labels_folder_val, dictionary, target_classes, num_classes)
    datasetVal.dataset_average = datasetTrain.dataset_average
    datasetVal.weights = datasetTrain.weights

    #AUGUMENTATION IS NOT APPLIED ON THE VALIDATION SET
    datasetVal.disableAugumentation()

    # setup the data loader
    dataloaderTrain = DataLoader(datasetTrain, batch_size=batch_sz, shuffle=flagShuffle, num_workers=0, drop_last=True,
                                 pin_memory=True)

    validation_batch_size = 4
    dataloaderVal = DataLoader(datasetVal, batch_size=validation_batch_size, shuffle=False, num_workers=0, drop_last=True,
                                 pin_memory=True)

    training_images_number = len(datasetTrain.images_names)
    validation_images_number = len(datasetVal.images_names)

    ###### SETUP THE NETWORK #####
    net = DeepLab(backbone='resnet', output_stride=16, num_classes=datasetTrain.num_classes)
    state = torch.load("deeplab-resnet.pth.tar")
    # RE-INIZIALIZE THE CLASSIFICATION LAYER WITH THE RIGHT NUMBER OF CLASSES, DON'T LOAD WEIGHTS OF THE CLASSIFICATION LAYER
    new_dictionary = state['state_dict']
    del new_dictionary['decoder.last_conv.8.weight']
    del new_dictionary['decoder.last_conv.8.bias']
    net.load_state_dict(state['state_dict'], strict=False)
    print("NETWORK USED: DEEPLAB V3+")

    # LOSS

    weights = datasetTrain.weights
    class_weights = torch.FloatTensor(weights).cuda()
    lossfn = nn.CrossEntropyLoss(weight=class_weights, ignore_index=-1)


    # OPTIMIZER
    # optimizer = optim.SGD(net.parameters(), lr=learning_rate, weight_decay=0.0002, momentum=0.9)
    optimizer = optim.Adam(net.parameters(), lr=learning_rate, weight_decay=L2_penalty)

    USE_CUDA = torch.cuda.is_available()

    if USE_CUDA:
        device = torch.device("cuda")
        net.to(device)

    ##### TRAINING LOOP #####

    scheduler = optim.lr_scheduler.ReduceLROnPlateau(optimizer, patience=2, verbose=True)

    best_accuracy = 0.0
    best_jaccard_score = 0.0


    print("Training Network")
    for epoch in range(epochs):  # loop over the dataset multiple times

        net.train()
        optimizer.zero_grad()
        running_loss = 0.0
        for i, minibatch in enumerate(dataloaderTrain):
            # get the inputs
            images_batch = minibatch['image']
            labels_batch = minibatch['labels']

            if USE_CUDA:
                images_batch = images_batch.to(device)
                labels_batch = labels_batch.to(device)

            # forward+loss+backward
            outputs = net(images_batch)
            loss = lossfn(outputs, labels_batch)
            loss.backward()

            # TO AVOID MEMORY TRUBLE UPDATE WEIGHTS EVERY BATCH SIZE X BATCH MULT
            if (i+1)% batch_mult == 0:
                optimizer.step()
                optimizer.zero_grad()

            print(epoch, i, loss.item())
            running_loss += loss.item()

        print("Epoch: %d , Running loss = %f" % (epoch, running_loss))


        ### VALIDATION ###
        if epoch > 0 and (epoch+1) % validation_frequency == 0:

            print("RUNNING VALIDATION.. ", end='')

            metrics_val, mean_loss_val = evaluateNetwork(dataloaderVal, datasetVal.weights, datasetVal.num_classes, net, flagTrainingDataset=False)
            accuracy = metrics_val['Accuracy']
            jaccard_score = metrics_val['JaccardScore']

            scheduler.step(mean_loss_val)

            metrics_train, mean_loss_train = evaluateNetwork(dataloaderTrain, datasetTrain.weights, datasetTrain.num_classes, net, flagTrainingDataset=True)
            accuracy_training = metrics_train['Accuracy']
            jaccard_training = metrics_train['JaccardScore']

            if jaccard_score > best_jaccard_score:

                best_accuracy = accuracy
                best_jaccard_score = jaccard_score
                torch.save(net.state_dict(), save_network_as)
                # performance of the best accuracy network on the validation dataset
                metrics_filename = save_network_as[:len(save_network_as) - 4] + "-val-metrics.txt"
                saveMetrics(metrics_val, metrics_filename)
                metrics_filename = save_network_as[:len(save_network_as) - 4] + "-train-metrics.txt"
                saveMetrics(metrics_train, metrics_filename)

            print("-> CURRENT BEST ACCURACY ", best_accuracy)

    print("***** TRAINING FINISHED *****")
    print("BEST ACCURACY REACHED ON THE VALIDATION SET: %.3f " % best_accuracy)


def testNetwork(images_folder, labels_folder, dictionary, nclasses, weights, average, classes, network_filename, output_folder):
    """
    Load a network and test it on the test dataset.g
    :param network_filename: Full name of the network to load (PATH+name)
    """

    # TEST DATASET
    datasetTest = CoralsDataset(images_folder, labels_folder, dictionary, None, 0)
    datasetTest.disableAugumentation()

    dataset.num_classes = loaded_dict["Num. Classes"]
    dataset.weights = np.array(loaded_dict["Weights"])
    dataset.dataset_average = np.array(loaded_dict["Average"])
    dataset.dict_target = loaded_dict["Classes"]

    batchSize = 4
    dataloaderTest = DataLoader(datasetTest, batch_size=batchSize, shuffle=False, num_workers=0, drop_last=True,
                            pin_memory=True)
    # DEEPLAB V3+
    net = DeepLab(backbone='resnet', output_stride=16, num_classes=datasetTest.num_classes)
    net.load_state_dict(torch.load(network_filename))
    print("Weights loaded.")

    metrics_test, loss = evaluateNetwork(dataloaderTest, datasetTest.weights, datasetTest.num_classes, net, False, output_folder)
    metrics_filename = network_filename[:len(network_filename) - 4] + "-test-metrics.txt"
    saveMetrics(metrics_test, metrics_filename)
    print("***** TEST FINISHED *****")
