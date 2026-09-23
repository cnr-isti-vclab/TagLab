
from ultralytics import YOLO
import yaml
import os
import sys



class TeeLogger:

    def __init__(self, callback):
        self.callback = callback
        self.stdout = sys.__stdout__

    def write(self, text):

        self.stdout.write(text)

        if self.callback and text.strip():
            self.callback(text.rstrip())

    def flush(self):
        self.stdout.flush()

def clearYoloCache(dataset_yaml):

    with open(dataset_yaml, "r") as f:
        data = yaml.safe_load(f)
    for split in ["train", "val", "test"]:
        path = data.get(split)
        if not path:
            continue
        labels_dir = path.replace( "images","labels")
        if not os.path.isdir(labels_dir):
            continue

        for fname in os.listdir(labels_dir):
            if fname.endswith(".cache"):
                cache_file = os.path.join(
                    labels_dir,
                    fname
                )
                try:
                    os.remove(cache_file)
                    print( f"Removed cache: "
                        f"{cache_file}"
                    )
                except Exception as e:
                    print(
                        f"Cannot remove "
                        f"{cache_file}: {e}"
                    )

def trainYOLOSeg(params,log_callback=None):



    dataset_yaml = params["dataset_yaml"]

    with open(dataset_yaml, "r") as f:
        dataset_info = yaml.safe_load(f)

    dataset_info["path"] = os.path.dirname(dataset_yaml)
    temp_yaml = os.path.join(os.path.dirname(dataset_yaml),"_taglab_dataset.yaml")

    with open(temp_yaml, "w") as f:
        yaml.safe_dump(
            dataset_info,
            f,
            sort_keys=False
        )

    if params.get("clear_cache", True):
        print("\nClearing YOLO cache...")
        clearYoloCache(params["dataset_yaml"])



    model_family = params.get(
        "model_family",
        "yolo11"
    )

    model_file = {

        "yolo11": {
            "n": os.path.join("models", "yolo11n-seg.pt"),
            "s": os.path.join("models", "yolo11s-seg.pt"),
            "m": os.path.join("models", "yolo11m-seg.pt"),
            "l": os.path.join("models", "yolo11l-seg.pt"),
            "x": os.path.join("models", "yolo11x-seg.pt"),
        },

        "yolo26": {
            "n": os.path.join("models", "yolo26n-seg.pt"),
            "s": os.path.join("models", "yolo26s-seg.pt"),
            "m": os.path.join("models", "yolo26m-seg.pt"),
            "l": os.path.join("models", "yolo26l-seg.pt"),
            "x": os.path.join("models", "yolo26x-seg.pt"),
        }
    }

    # model = YOLO(model_file[params["model_size"]])
    weights = model_file[model_family][params["model_size"]]
    model = YOLO(weights)
    selected_ids = []
    selected_classes = params.get("selected_classes",[])

    base_epochs = params["epochs"]
    extra_epochs = params.get("extra_epochs_factor", 0)
    params["epochs"] = int(round(base_epochs * (1.0 + extra_epochs)))

    if selected_classes:
        with open(dataset_yaml, "r") as f:
            dataset_info = yaml.safe_load(f)
        names = dataset_info["names"]
        for cls_id, cls_name in names.items():
            if cls_name in selected_classes:
                selected_ids.append(
                    int(cls_id)
                )

    train_args = {

        "epochs": params["epochs"],
        "batch": params["batch"],
        "imgsz": params["imgsz"],

        "degrees": params["degrees"],
        "translate": params["translate"],
        "scale": params["scale"],
        "shear": params["shear"],
        "perspective": params["perspective"],

        "flipud": params["flipud"],
        "fliplr": params["fliplr"],

        "hsv_h": params["hsv_h"],
        "hsv_s": params["hsv_s"],
        "hsv_v": params["hsv_v"],

        "copy_paste": params["copy_paste"],
        "mosaic": params["mosaic"],
        "close_mosaic": params["close_mosaic"],

        "box": params["box"],
        "cls": params["cls"],
        "dfl": params["dfl"],

        "dropout": params["dropout"],
        "warmup_epochs": params["warmup_epochs"],

        "cos_lr": params["cos_lr"],
        "patience": params["patience"],

        "mask_ratio": params["mask_ratio"],
        "workers": params["workers"],
        "amp": params["amp"],

        "overlap_mask": params["overlap_mask"],

        "name": params["name"],
        "save": True,}



    train_args["data"] = temp_yaml
    train_args["close_mosaic"] = int(train_args.get("close_mosaic", 0))

    scale_value = train_args.get("scale")

    if isinstance(scale_value, (list, tuple)):
        train_args["scale"] = max(
            abs(1.0 - scale_value[0]),
            abs(scale_value[1] - 1.0)
        )

    if selected_ids:

        train_args["classes"] = (selected_ids)
        print( f"Training selected classes: "f"{selected_classes}" )
        print(
            f"YOLO IDs: "
            f"{selected_ids}"
        )


    print(train_args)
    print("\nYOLO TRAINING CONFIGURATION")
    old_stdout = sys.stdout

    if log_callback:
        sys.stdout = TeeLogger(
            log_callback
        )

    try:

        # run training
        if log_callback:

            log_callback(
                "\nFINAL YOLO ARGUMENTS\n"
            )

            for k, v in train_args.items():
                log_callback(
                    f"{k}: {v}"
                )

        results = model.train( **train_args)

        # run validation on best model

        best_model_path = os.path.join(model.trainer.save_dir,"weights","best.pt")
        best_model = YOLO(best_model_path)

        metrics = best_model.val(data=dataset_yaml,
            imgsz= train_args.get("imgsz",1024),
            conf= 0.5, # filter out allucinations
            iou= 0.7, # this parameter helps to handle dense colonies
            split= "val",
            save_json= True,
            plots= True # generate a new cf
        )

        print("\n--- VALIDATION RESULTS ---")

        try:
            print(f"--- Results at 0.5 confidence")
            print(f"mAP50-95 (Box): {results.box.map:.3f}")
            print(f"mAP50-95 (Mask): {results.seg.map:.3f}")
            print(f"Precision Globale: {results.box.mp:.3f}")
            print(f"Recall Globale: {results.box.mr:.3f}")

        except Exception as e:
            print( f"Cannot print metrics: {e}")

        # EXPORT
        export_path = model.export(
            format="onnx"
        )
        print(
            f"\nModel exported to:\n"
            f"{export_path}"
        )

        return {
            "results":
                results,

            "metrics":
                metrics,

            "export_path":
                export_path }
    finally:

        sys.stdout = old_stdout


