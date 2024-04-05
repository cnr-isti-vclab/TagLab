import os
import glob
import time
import random
import argparse
import traceback

import concurrent.futures

from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

from Common import IMG_FORMATS
from Common import CORALNET_URL

from Browser import login
from Browser import authenticate
from Browser import check_permissions
from Browser import check_for_browsers


# -----------------------------------------------------------------------------
# Functions
# -----------------------------------------------------------------------------
def upload_multi_images(driver, source_id, images, prefix):
    """
    Upload multiple sets of images concurrently.
    """

    def setup_browsers(username, password):
        """
        Set up a new WebDriver instance.
        """
        # Create a new browser
        new_driver = check_for_browsers(True)

        # Pass in credentials
        new_driver.capabilities['credentials'] = {
            'username': username,
            'password': password
        }
        # Login
        new_driver, _ = login(new_driver)

        return new_driver

    # Create multiple drivers
    print("\n###############################################")
    print("Multi Image Upload")
    print("###############################################\n")

    # Number of additional browsers
    N = 10

    print(f"NOTE: Opening {N} additional browsers, please wait")

    # Extract the credentials from the original driver
    username = driver.capabilities['credentials']['username']
    password = driver.capabilities['credentials']['password']

    drivers = []

    # Use concurrent.futures to set up N drivers concurrently
    with concurrent.futures.ThreadPoolExecutor(max_workers=N) as executor:
        for _ in range(N):
            drivers.append(executor.submit(setup_browsers, username, password).result())

    # Shuffle the image list
    random.shuffle(images)

    # Divide images among browsers using round-robin distribution
    image_chunks = [[] for _ in range(N)]

    for i, image in enumerate(images):
        driver_index = i % len(drivers)
        image_chunks[driver_index].append(image)

    print("\n###############################################")
    print("Uploading Images")
    print("###############################################\n")

    print(f"NOTE: Created {N} browsers, each tasked with {len(image_chunks)} images")

    # Use concurrent.futures to upload each chunk of images with a separate driver
    with concurrent.futures.ThreadPoolExecutor(max_workers=N) as executor:
        for i in range(N):
            executor.submit(upload_images, drivers[i], source_id, image_chunks[i], prefix)

    # Close the additional drivers
    for d_idx, d in enumerate(drivers):
        print(f"NOTE: Closing browser {d_idx + 1}")
        d.quit()

    # Return the original driver
    return driver


def upload_images(driver, source_id, images, prefix):
    """
    Upload images to CoralNet.
    """

    print("\nNavigating to image upload page...")

    # Variable for success
    success = False

    # Go to the upload page
    driver.get(CORALNET_URL + f"/source/{source_id}/upload/images/")

    # First check that this is existing source the user has access to
    try:
        # Check the permissions
        driver, status = check_permissions(driver)

        # Check the status
        if "Page could not be found" in status.text:
            raise Exception(f"ERROR: {status.text.split('.')[0]}")

    except Exception as e:
        print(f"ERROR: {e} or you do not have permission to access it")
        return driver, success

    # Send the files to CoralNet for upload
    try:
        # Locate the prefix input field
        path = "id_name_prefix"
        prefix_input = WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.ID, path)))

        # Check if the prefix input field is enabled
        if prefix_input.is_enabled():
            print("NOTE: Prefix input field is enabled")
            print(f"NOTE: Attempting to send prefix")
            prefix_input.send_keys(prefix)

            # Moves cursor away from prefix box, needed.
            path = "narrow_column"
            narrow_column = WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.CLASS_NAME, path)))

            narrow_column.click()

        else:
            # Prefix input field is not enabled, something is wrong
            raise ValueError("ERROR: Prefix input field is not enabled; exiting.")

        # Locate the file input field
        path = "//input[@type='file'][@name='files']"
        file_input = WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.XPATH, path)))

        # Check if the file input field is enabled
        if file_input.is_enabled():
            print(f"NOTE: File input field is enabled")
            print(f"NOTE: Attempting to upload {len(images)} images")
            file_input.send_keys("\n".join(images))

        else:
            # File input field is not enabled, something is wrong
            raise ValueError(
                "ERROR: File input field is not enabled; exiting.")

    except Exception as e:
        print(f"ERROR: Could not submit files for upload\n{e}")
        return success

    # Attempt to upload the files to Tools
    try:
        # Check if files can be uploaded
        path = "status_display"
        status = WebDriverWait(driver, len(images)).until(
            EC.presence_of_element_located((By.ID, path)))

        # If there are many files, they will be checked
        while "Checking files..." in status.text:
            continue

        # Give the upload status time to update
        time.sleep(3)

        # Get the pre-upload status
        path = "pre_upload_summary"
        pre_status = WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.ID, path)))

        # Print the pre-upload status
        print(f"\n{pre_status.text}\n")

        # Images can be uploaded
        if "Ready for upload" in status.text:

            # Wait for the upload button to appear
            path = "//button[@id='id_upload_submit']"
            upload_button = WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.XPATH, path)))

            # Check if the upload button is enabled
            if upload_button.is_enabled():
                # Click the upload button
                upload_button.click()

                # Print the status
                print(f"NOTE: {status.text}")

                # Give the upload status time to update
                time.sleep(3)

                # Get the mid-upload status
                path = "mid_upload_summary"
                mid_status = WebDriverWait(driver, 10).until(
                    EC.presence_of_element_located((By.ID, path)))

                while "Uploading..." in status.text:
                    new_upload_status_text = mid_status.text
                    if new_upload_status_text != mid_status.text:
                        new_upload_status_text = mid_status.text
                        print(f"NOTE: {new_upload_status_text}")
                        time.sleep(1)
                    continue

                # Give the upload status time to update
                time.sleep(3)

                if "Upload complete" in status.text:
                    print(f"NOTE: {status.text}")
                    success = True
                else:
                    print(f"ERROR: {status.text}")

        # Images cannot be uploaded because they already exists
        elif "Cannot upload any of these image files" in status.text:
            print(f"NOTE: {status.text}, they already exist in source.")
            success = True

        # Unexpected status
        else:
            print(f"Warning: {status.text}")

    except Exception as e:
        print(f"ERROR: Issue with uploading images. \n{e}")

    time.sleep(3)

    return driver, success


def upload_labelset(driver, source_id, labelset):
    """
    Upload labelsets to CoralNet.
    """

    print("\nNOTE: Navigating to labelset upload page")

    # Create a variable to track the success of the upload
    success = False

    # Go to the upload page
    driver.get(CORALNET_URL + f"/source/{source_id}/labelset/import/")

    # First check that this is existing source the user has access to
    try:
        # Check the permissions
        driver, status = check_permissions(driver)

        # Check the status
        if "Page could not be found" in status.text:
            raise Exception(f"ERROR: {status.text.split('.')[0]}")

    except Exception as e:
        print(f"ERROR: {e} or you do not have permission to access it")
        return driver, success

    # Check if files can be uploaded, get the status for the page
    path = "status_display"
    status = WebDriverWait(driver, 10).until(
        EC.presence_of_element_located((By.ID, path)))

    # Get the status details for the page
    path = "status_detail"
    status_details = WebDriverWait(driver, 10).until(
        EC.presence_of_element_located((By.ID, path)))

    try:
        # Locate the file input field
        path = "//input[@type='file'][@name='csv_file']"
        file_input = WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.XPATH, path)))

        # Check if the file input field is enabled
        if file_input.is_enabled():
            # Submit the file
            print(f"NOTE: File input field is enabled")
            print(f"NOTE: Uploading {os.path.basename(labelset)}")
            file_input.send_keys(labelset)

            # Give the upload status time to update
            time.sleep(5)

            # Check the status
            if "Save labelset" in status.text:

                # Wait for the upload button to appear
                path = "//button[@id='id_upload_submit']"
                upload_button = WebDriverWait(driver, 10).until(
                    EC.presence_of_element_located((By.XPATH, path)))

                # Click the upload button
                upload_button.click()

                # Give the upload status time to update
                time.sleep(5)

                # Check the status,
                if "Labelset saved" in status.text:
                    print(f"NOTE: {status.text}")
                    success = True

            elif "Error" in status.text:
                # The file is not formatted correctly
                raise Exception(f"ERROR: {status.text}\n"
                                f"ERROR: {status_details.text}")
            else:
                # File input field is enabled, but something is wrong
                raise Exception(f"ERROR: Could not upload {labelset}")
        else:
            # File input field is not enabled, something is wrong
            raise Exception("ERROR: File input field is not enabled; exiting.")

    except Exception as e:
        print(f"ERROR: Could not submit file for upload\n{e}")

    time.sleep(3)

    return driver, success


def upload_annotations(driver, source_id, annotations):
    """
    Upload annotations to CoralNet.
    """

    print("\nNOTE: Navigating to annotation upload page")

    # Create a variable to track the success of the upload
    success = False

    # If there are already annotations, some will be overwritten
    alert = False

    # Go to the upload page
    driver.get(CORALNET_URL + f"/source/{source_id}/upload/annotations_csv/")

    # First check that this is existing source the user has access to
    try:
        # Check the permissions
        driver, status = check_permissions(driver)

        # Check the status, user doesn't have permission
        if "Page could not be found" in status.text:
            raise Exception(f"ERROR: {status.text.split('.')[0]} or you do not"
                            f" have permission to access it")

        # Check the status, source doesn't have a labelset yet
        if "create a labelset before uploading annotations" in status.text:
            raise Exception(f"ERROR: {status.text.split('.')[0]}")

    except Exception as e:
        print(f"{e}")
        return driver, success

    # Check if files can be uploaded, get the status for the page
    path = "status_display"
    status = WebDriverWait(driver, 10).until(
        EC.presence_of_element_located((By.ID, path)))

    # Get the status details for the page
    path = "status_detail"
    status_details = WebDriverWait(driver, 10).until(
        EC.presence_of_element_located((By.ID, path)))

    try:
        # Locate the file input field
        path = "//input[@type='file'][@name='csv_file']"
        file_input = WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.XPATH, path)))

        # Check if the file input field is enabled
        if file_input.is_enabled():

            # Submit the file
            print(f"NOTE: File input field is enabled")
            print(f"NOTE: Uploading {os.path.basename(annotations)}")
            file_input.send_keys(annotations)

            print(f"NOTE: {status.text}")

            # Give the upload status time to update
            time.sleep(3)

            # Wait while the annotations are processing
            while "Processing" in status.text:
                continue

            # If there was an error, raise an exception
            if "Error" in status.text:
                # The file is not formatted correctly
                raise Exception(f"ERROR: {status.text}\n"
                                f"ERROR: {status_details.text}")

            # Data was sent successfully
            elif "Data OK" in status.text:

                # Print the status details
                print(f"\n{status_details.text}\n")

                if "deleted" in status_details.text:
                    alert = True

                # Wait for the upload button to appear
                path = "//button[@id='id_upload_submit']"
                upload_button = WebDriverWait(driver, 10).until(
                    EC.presence_of_element_located((By.XPATH, path)))

                # Click the upload button
                upload_button.click()

                # There are already annotations for these files, overwrite them
                if alert:
                    # Wait for the alert dialog to appear
                    alert = WebDriverWait(driver, 10).until(
                        EC.alert_is_present())

                    # Switch to the alert dialog
                    alert = driver.switch_to.alert

                    # Accept the alert (OK button)
                    alert.accept()

                    # Switch back to the main content
                    driver.switch_to.default_content()

                # Give the upload status time to update
                time.sleep(3)

                # Get the status for the page
                print(f"NOTE: {status.text}")

                # Wait while the annotations are saving
                while "Saving" in status.text:
                    continue

                # Check if the annotations were saved successfully
                if "saved" in status.text:
                    print(f"NOTE: {status.text}")
                    success = True
                else:
                    # The annotations were not saved successfully
                    raise Exception(f"ERROR: {status.text}"
                                    f"{status_details.text}")

        else:
            # File input field is not enabled, something is wrong
            raise Exception("ERROR: File input field is not enabled; exiting.")

    except Exception as e:
        print(f"ERROR: Could not upload annotations.\n{e}")

    time.sleep(3)

    return driver, success


def upload(args):
    """
    Upload function that takes in input from argparse (cmd, or gui),
    and initiates the uploading
    """

    print("\n###############################################")
    print("Upload")
    print("###############################################\n")

    # -------------------------------------------------------------------------
    # Prepare the data
    # -------------------------------------------------------------------------
    # Flags to determine what to upload
    labelset_upload = False
    image_upload = False
    annotation_upload = False

    # Check if there is a labelset to upload
    if args.labelset != "":
        labelset = os.path.abspath(args.labelset)

        if os.path.exists(labelset) and "csv" in labelset.split(".")[-1]:
            print(f"NOTE: Found labelset to upload")
            labelset_upload = True
        else:
            print(f"NOTE: No valid labelset found in {labelset}")

    # Data to be uploaded
    if args.images != "":
        images = os.path.abspath(args.images)
        images = glob.glob(images + "/*.*")
        images = [i for i in images if i.split('.')[-1].lower() in IMG_FORMATS]

        # Check if there are images to upload
        if len(images) > 0:
            print(f"NOTE: Found {len(images)} images to upload")
            image_upload = True
        else:
            print(f"NOTE: No valid images found in {args.images}")

    # Add a dash to prefix if it's being used, and isn't already there
    if args.prefix != "":
        prefix = args.prefix
        prefix = f"{prefix}-" if prefix[-1] != "-" else prefix
    else:
        prefix = ""

    # Check if there are annotations to upload
    if args.annotations != "":
        # Assign the annotations
        annotations = os.path.abspath(args.annotations)

        if os.path.exists(annotations) and "csv" in annotations.split(".")[-1]:
            print(f"NOTE: Found annotations to upload")
            annotation_upload = True
        else:
            print(f"NOTE: No valid annotations found in {annotations}")

    # If there are no images, labelset, or annotations to upload, exit
    if not image_upload and not labelset_upload and not annotation_upload:
        print(f"ERROR: No data to upload. Please check the following files:\n"
              f"Images: {args.images}\n"
              f"Labelset: {args.labelset}\n"
              f"Annotations: {args.annotations}")
        return

    # ID of the source to upload data to
    source_id = args.source_id

    # -------------------------------------------------------------------------
    # Authenticate the user
    # -------------------------------------------------------------------------

    try:
        username = args.username
        password = args.password

        # Ensure the user provided a username and password.
        authenticate(username, password)
    except Exception as e:
        print(f"ERROR: Could not download data.\n{e}")
        return

    # -------------------------------------------------------------------------
    # Get the browser
    # -------------------------------------------------------------------------

    # Pass the options object while creating the driver
    driver = check_for_browsers(args.headless)
    # Store the credentials in the driver
    driver.capabilities['credentials'] = {
        'username': username,
        'password': password
    }

    # -------------------------------------------------------------------------
    # Upload the data
    # -------------------------------------------------------------------------

    # Log in to CoralNet
    driver, _ = login(driver)

    # Upload labelset
    if labelset_upload:
        driver, _ = upload_labelset(driver, source_id, labelset)

    # Upload images
    if image_upload:
        # If there's many images, use multi upload
        if len(images) >= 1000:
            driver = upload_multi_images(driver, source_id, images, prefix)
        else:
            driver, _ = upload_images(driver, source_id, images, prefix)

    # Upload annotations
    if annotation_upload:
        driver, _ = upload_annotations(driver, source_id, annotations)

    # Close the browser
    driver.close()


# -----------------------------------------------------------------------------
# Main
# -----------------------------------------------------------------------------

def main():
    """
    This is the main function for the script. Users can upload images,
    labelsets, and annotations to CoralNet via command line. First a browser
    is checked for, then the user's credentials are checked. Data is checked to
    exist, and then uploaded to Tools.

    If a user tries to upload data they do no have permissions to, the script
    will exit. If a user tries to upload data to a source that does not exist,
    the script will exit. If a user tries to upload annotations to a source
    that does not have a complete labelset or corresponding images, the script
    will exit. In general, it's dummy proofed to prevent users from uploading
    data that will not work.

    If annotations already exist for an image, they will be overwritten. If
    images already exist for a source, they will be skipped. If a labelset
    already exists for a source, it will be added.
    """

    parser = argparse.ArgumentParser(description='Upload arguments')

    parser.add_argument('--username', type=str,
                        default=os.getenv('CORALNET_USERNAME'),
                        help='Username for CoralNet account')

    parser.add_argument('--password', type=str,
                        default=os.getenv('CORALNET_PASSWORD'),
                        help='Password for CoralNet account')

    parser.add_argument('--source_id', type=int,
                        help='Source ID to upload to.')

    parser.add_argument('--images', type=str,
                        help='A directory where all images are located')

    parser.add_argument('--prefix', type=str, default="",
                        help='Prefix to add to each image basename')

    parser.add_argument('--annotations', type=str, default="",
                        help='The path to the annotations file')

    parser.add_argument('--labelset', type=str, default="",
                        help='The path to the labelset file')

    parser.add_argument('--headless', action='store_true', default=True,
                        help='Run browser in headless mode')

    args = parser.parse_args()

    try:
        # Call the upload function
        upload(args)
        print("Done.\n")

    except Exception as e:
        print(f"ERROR: {e}")
        print(traceback.format_exc())


if __name__ == "__main__":
    main()