import os
import time
import json
import glob
import requests
import datetime
import argparse
import traceback

import re
import math
import pandas as pd

from Common import get_now

from Browser import login
from Browser import get_token
from Browser import authenticate
from Browser import CORALNET_URL

from Download import get_images
from Download import get_image_urls
from Download import download_metadata
from Download import check_for_browsers


# -----------------------------------------------------------------------------
# Functions
# -----------------------------------------------------------------------------


def get_source_meta(driver, source_id_1, source_id_2=None, prefix=None, image_list=None):
    """
    Downloads just the information from source needed to do API calls;
    source id 1 refers to the source containing images, and source id 2
    refers to a source for a different model (if desired)
    """

    # Variables for the model
    source_id = source_id_1 if source_id_2 is None else source_id_2

    print("\n###############################################")
    print(f"Downloading Source Metadata {source_id}")
    print("###############################################\n")

    # Get the metadata
    driver, meta = download_metadata(driver, source_id)

    # Check if a model exists
    if meta is None:
        raise Exception(f"ERROR: No model found for the source {source_id}.")

    # Get the images for the source
    driver, source_images = get_images(driver, source_id_1, prefix, image_list)

    # Check if there are any images
    if source_images is None:
        raise Exception(f"ERROR: No images found in the source {source_id_1}.")

    return driver, meta, source_images


def in_N_seconds(wait):
    """
    Calculate the time in N seconds from the current time.
    """
    # Get the current time, and add the wait time
    now = datetime.datetime.now()
    then = now + datetime.timedelta(seconds=wait)
    return then.strftime("%H:%M:%S")


def is_expired(url):
    """
    Calculates the time remaining before a URL expires, based on its "Expires"
    timestamp.
    """
    # Assume the URL is expired
    expired = True
    # Set the time remaining to 0
    time_remaining = 0

    try:
        # Extract expiration timestamp from URL
        match = re.search(r"Expires=(\d+)", url)

        # If the timestamp was found, extract it
        if match:
            # Convert the timestamp to an integer
            expiration = int(match.group(1))

            # Calculate time remaining before expiration
            time_remaining = expiration - int(time.time())
        else:
            raise ValueError(f"ERROR: Could not find expiration timestamp in \n{url}")

    except Exception as e:
        print(f"{e}")

    # Check the amount of time remaining
    if time_remaining >= 200:
        expired = False

    return expired


def get_expiration(url):
    """

    """
    try:
        # Extract expiration timestamp from URL
        match = re.search(r"Expires=(\d+)", url)

        # If the timestamp was found, extract it
        if match:
            # Convert the timestamp to an integer
            expiration = int(match.group(1))

            # Calculate time remaining before expiration
            time_remaining = expiration - int(time.time())

        else:
            raise ValueError(f"ERROR: Could not find expiration timestamp in \n{url}")

    except Exception as e:
        time_remaining = 0
        print(f"{e}")

    return time_remaining


def check_job_status(response, coralnet_token):
    """
    Sends a request to retrieve the completed annotations and returns the
    status update.
    """

    # Create the payload
    url = f"https://coralnet.ucsd.edu{response.headers['Location']}"
    headers = {"Authorization": f"Token {coralnet_token}"}
    # Sends a request to retrieve the completed annotations
    status = requests.get(url=url, headers=headers)
    # Convert the response to JSON
    current_status = json.loads(status.content)
    wait = 1

    if status.ok:
        # Still in progress
        if 'status' in current_status['data'][0]['attributes'].keys():
            # Extract the status information
            s = current_status['data'][0]['attributes']['successes']
            f = current_status['data'][0]['attributes']['failures']
            t = current_status['data'][0]['attributes']['total']
            status_str = current_status['data'][0]['attributes']['status']
            ids = current_status['data'][0]['id'].split(",")
            ids = ''.join(str(_) for _ in ids)
            # Get the current time
            now = time.strftime("%H:%M:%S")
            # Create the message
            message = "\nJOB ID {: <8} Status: {: <8}\n".format(ids, status_str)
            message += "Images: {: <8} " \
                       "Predictions: {: <8} " \
                       "Failures: {: <8} " \
                       "Time: {: <8}".format(t, s, f, now)
        else:
            # It's done with all images
            message = "\nNOTE: Completed Job!"
    else:
        # CoralNet is getting too many requests, sleep for a second.
        message = f"Tools: {current_status['errors'][0]['detail']}"
        try:
            # Try to wait the amount of time requested by Tools
            match = re.search(r'\d+', message)
            wait = int(match.group())
        except:
            wait = 30

    return current_status, message, wait


def print_job_status(payload_imgs, active, completed):
    """
    Print the current status of jobs and images being processed.
    """
    print("\nSTATUS: "
          "Images in Queue: {: <8} "
          "Active Jobs: {: <8} "
          "Completed Jobs: {: <8}".format(len(payload_imgs), len(active), len(completed)))


def convert_to_csv(status, image_names):
    """
    Converts response data into a Pandas DataFrame and concatenates each row
    into a single DataFrame.
    """

    print(f"NOTE: Recording annotations for completed job")

    # A list to store all the model predictions (dictionaries)
    model_predictions_list = []

    for data, image_name in zip(status['data'], image_names):
        # Extract the point information if it was returned
        if 'points' in data['attributes']:
            for point in data['attributes']['points']:
                p = dict()
                p['Name'] = image_name
                p['Row'] = point['row']
                p['Column'] = point['column']

                for index, classification in enumerate(point['classifications']):
                    p['Machine confidence ' + str(index + 1)] = classification['score']
                    p['Machine suggestion ' + str(index + 1)] = classification['label_code']

                model_predictions_list.append(p)
                
        # If there aren't points, there was an error: print it
        elif 'errors' in data['attributes']:
            print(f"ERROR: {data['attributes']['errors'][0]}")

    # Create a single DataFrame from the list of dictionaries
    model_predictions = pd.DataFrame(model_predictions_list)

    if model_predictions.empty:
        print("WARNING: Predictions returned from CoralNet were empty!")

    return model_predictions


def submit_jobs(driver, source_id_1, source_id_2, prefix, images_w_points, points, output_dir):
    """

    """
    # -----------------------------
    # Get Source information
    # -----------------------------
    try:
        source_id = source_id_1
        driver, meta, source_images = get_source_meta(driver,
                                                      source_id_1,
                                                      source_id_2,
                                                      prefix,
                                                      images_w_points)

        if meta is None:
            raise Exception(f"ERROR: Cannot make predictions using Source {source_id}")

        # Get the images desired for predictions; make sure it's not file path.
        images = points['Name'].unique().tolist()
        images = [os.path.basename(image) for image in images]
        # Get the information needed from the source images dataframe
        images = source_images[source_images['Name'].isin(images)].copy()
        print(f"NOTE: Found {len(images)} images in source {source_id}")

        if len(images) != len(points['Name'].unique()):
            # Let the user know that not all images in points file
            # are actually on CoralNet.
            print(f"WARNING: Points file has points for {len(points['Name'].unique())} images, "
                  f"but only {len(images)} of those images were found on CoralNet.")

            # Let them exit if they want
            time.sleep(5)

    except Exception as e:
        print(f"ERROR: Issue with getting Source Metadata.\n{e}")
        return

    # Set the model ID and URL
    model_id = meta['Global id'].max()
    model_url = CORALNET_URL + f"/api/classifier/{model_id}/deploy/"

    # Set the data root directory (parent to source dir)
    output_dir = f"{os.path.abspath(output_dir)}/predictions/"
    os.makedirs(output_dir, exist_ok=True)

    # Final CSV containing predictions
    predictions_path = f"{output_dir}coralnet_{get_now()}_predictions.csv"

    print("\n###############################################")
    print(f"Getting Predictions from Model {model_id} Source {source_id}")
    print("###############################################")

    # Jobs that are currently active
    active_jobs = []
    active_imgs = []
    # Jobs that are completed
    completed_jobs = []
    completed_imgs = []
    # Flag to indicate if all images have been passed to model
    finished = False
    # The amount of time to wait before checking the status of a job
    patience = 75

    # To hold all the coralnet api predictions (sorted later)
    coralnet_predictions = []

    # The number of images, points to include in each job
    data_batch_size = 100
    point_batch_size = 200
    active_job_limit = 5

    # A list for images and data that have been sampled this round
    payload_data = []
    payload_imgs = []

    for name in images['Name'].unique():

        # Get the points for just this image
        p = points[points['Name'] == name]
        # Because CoralNet isn't consistent...
        p = p.rename(columns={'Row': 'row', 'Column': 'column'})
        p = p[['row', 'column']].to_dict(orient="records")

        # Split points into batches of 200
        if len(p) > point_batch_size:
            print(f"NOTE: {name} has {len(p)} points, "
                  f"separating into {math.ceil(len(p) / point_batch_size)} 'images'")

        for i in range(0, len(p), point_batch_size):
            # Add the data to the list for payloads
            payload_imgs.append(name)
            # Get the batch of points
            batch_points = p[i:i + point_batch_size]
            # Add data to payload
            if batch_points:
                payload_data.append(
                    {
                        "type": "image",
                        "attributes": {
                            "name": name,
                            "url": None,
                            "points": batch_points
                        }
                    })

    # Total number of images
    total_images = len(payload_imgs)
    print(f"\nNOTE: Queuing {total_images} images, {math.ceil(total_images / data_batch_size)} jobs\n")

    # All payloads are preprocessed, now all they need are their
    # image urls, which will happen right before they are submitted
    # as job. When requested, the URLs last 1 hour before expiring.
    while not finished:

        # There must be room for more active jobs and there must still be
        # preprocessed payloads to be able to submit a new job, otherwise
        # this section is skipped; and of course, images to add.
        while len(active_jobs) < active_job_limit and len(payload_imgs):

            # Here we initialize the payload, which is a JSON object that
            # contains the image URLs and their points; payloads will contain
            # batches of data (N = data_batch_size).

            # Get the image names and their pages
            image_names = payload_imgs[:data_batch_size]
            images_payload = images[images['Name'].isin(image_names)].copy()
            # Get the URLs of the current set of image (1 hour starts now)
            driver, image_urls = get_image_urls(driver, images_payload['Image Page'].tolist())
            images_payload['Image URL'] = image_urls

            # Get the data for the current payload
            payload = {'data': payload_data[:data_batch_size]}

            # Before submitting it to CoralNet, pass in the url
            # that was just retrieved.
            for p in payload['data']:
                url = images_payload[images_payload['Name'] == p['attributes']['name']]['Image URL'].values[0]
                p['attributes']['url'] = url

            # Use the payload to construct the job
            job = {
                "headers": driver.capabilities['credentials']['headers'],
                "model_url": model_url,
                "image_names": image_names,
                "data": json.dumps(payload, indent=4),
            }

            # Upload the image and the sampled points to Tools
            print(f"NOTE: Attempting to upload {len(image_names)} images as a job")

            # Sends the requests to the `source` and in exchange, receives
            # a message telling if it was received correctly.
            response = requests.post(url=job["model_url"],
                                     data=job["data"],
                                     headers=job["headers"])
            if response.ok:
                # If it was received
                print(f"NOTE: Successfully uploaded {len(image_names)} images as a job\n")

                # Add to active jobs
                active_jobs.append(response)
                active_imgs.append(image_names)

                # Remove the used indices from payload_imgs and payload_data
                payload_imgs = payload_imgs[data_batch_size:]
                payload_data = payload_data[data_batch_size:]

            else:
                # There was an error uploading to Tools; get the message
                message = json.loads(response.text)['errors'][0]['detail']

                # Print the message
                print(f"CoralNet: {message}")

                if "5 jobs active" in message:
                    # Max number of jobs reached, so we need to wait
                    print(f"\nNOTE: Will attempt again at {in_N_seconds(patience)}")
                    time.sleep(patience)

        # At this point, either active_job_limit is reached
        # or there are no more data in payload_imgs, we just wait
        print_job_status(payload_imgs, active_jobs, completed_jobs)

        # Check the status of the active jobs, break when another can be added
        while len(active_jobs) <= active_job_limit and len(active_jobs) != 0:

            # Sleep before checking status again
            print(f"\nNOTE: Checking status again at {in_N_seconds(patience)}")
            time.sleep(patience)

            # Loop through the active jobs
            for i, (job, names) in enumerate(list(zip(active_jobs, active_imgs))):

                # Check the status of the current job
                current_status, message, wait = check_job_status(job, driver.capabilities['credentials']['token'])

                # Print the message
                print(f"{message}")

                # Current job finished, output the results, remove from queue
                if "Completed" in message:
                    # Convert to csv, and save locally, check for expired images
                    predictions = convert_to_csv(current_status, names)

                    # Add to completed jobs list
                    print(f"NOTE: Adding {len(names)} images to completed")
                    completed_imgs.extend(names)
                    completed_jobs.append(current_status)

                    # Remove from active jobs, images list
                    print(f"NOTE: Removing {len(names)} images from active\n")
                    active_imgs.remove(names)
                    active_jobs.remove(job)

                    # Store the coralnet predictions for sorting later
                    coralnet_predictions.append(predictions)

                # Wait for the specified time before checking the status again
                time.sleep(wait)

            # Check the status of the active jobs
            print_job_status(payload_imgs, active_jobs, completed_jobs)

            # After checking the current status, break if another job can be added
            # Else wait and check the status of the active jobs again.
            if len(active_jobs) < active_job_limit and payload_imgs:
                print(f"\nNOTE: Active jobs is {len(active_jobs)}, "
                      f"images in queue is {len(payload_imgs)}; adding more.\n")
                break

        # Check to see everything has been completed, breaking the loop
        if not active_jobs and not payload_imgs:
            print("\nNOTE: All images have been processed; exiting loop.\n")
            finished = True

    # Sort predictions to match original points file, keep original columns
    print("NOTE: Sorting predictions to align with original file provided")
    final_predictions = pd.concat(coralnet_predictions)
    final_predictions = pd.merge(points, final_predictions, on=['Name', 'Row', 'Column'])

    # Output to disk
    print(f"NOTE: CoralNet predictions saved to {os.path.basename(predictions_path)}")
    final_predictions.to_csv(predictions_path)

    return driver, final_predictions, predictions_path


def api(args):
    """

    """
    print("\n###############################################")
    print(f"API")
    print("###############################################")

    # -------------------------------------------------------------------------
    # Check the data
    # -------------------------------------------------------------------------
    try:

        # Check to see if the csv file exists
        assert os.path.exists(args.points)

        # Determine if it's a single file or a folder
        if os.path.isfile(args.points):
            # If a file, just read it in
            points = pd.read_csv(args.points, index_col=0)
        elif os.path.isdir(args.points):
            # If a folder, read in all csv files, concatenate them together
            csv_files = glob.glob(args.points + "/*.csv")
            points = pd.DataFrame()
            for csv_file in csv_files:
                points = pd.concat([points, pd.read_csv(csv_file, index_col=0)])
        else:
            raise Exception(f"ERROR: {args.points} is invalid.")

        # Check to see if the csv file has the expected columns
        assert 'Name' in points.columns
        assert 'Row' in points.columns
        assert 'Column' in points.columns
        assert len(points) > 0

        images_w_points = points['Name'].to_list()

    except Exception as e:
        raise Exception(f"ERROR: File(s) provided do not match expected format!\n{e}")

    # -------------------------------------------------------------------------
    # Authenticate the user
    # -------------------------------------------------------------------------
    try:
        # Username, Password
        username = args.username
        password = args.password
        authenticate(username, password)
        coralnet_token, headers = get_token(username, password)
    except Exception as e:
        raise Exception(f"ERROR: {e}")

    # -------------------------------------------------------------------------
    # Get the browser
    # -------------------------------------------------------------------------
    driver = check_for_browsers(headless=True)
    # Store the credentials in the driver
    driver.capabilities['credentials'] = {
        'username': username,
        'password': password,
        'headers': headers,
        'token': coralnet_token
    }
    # Login to Tools
    driver, _ = login(driver)

    # Submit the jobs
    driver, final_predictions, predictions_path = submit_jobs(driver,
                                                              args.source_id_1,
                                                              args.source_id_2,
                                                              args.prefix,
                                                              images_w_points,
                                                              points,
                                                              args.output_dir)
    # Close the browser
    driver.close()


# -----------------------------------------------------------------------------
# Main Function
# -----------------------------------------------------------------------------

def main():
    """
    This is the main part of the script. We loop through each image, get the
    points for that image, and then make predictions for those points. We then
    save the predictions to a CSV file in the predictions' directory.
    """

    parser = argparse.ArgumentParser(description='API arguments')

    parser.add_argument('--username', type=str,
                        default=os.getenv('CORALNET_USERNAME'),
                        help='Username for CoralNet account')

    parser.add_argument('--password', type=str,
                        default=os.getenv('CORALNET_PASSWORD'),
                        help='Password for CoralNet account')

    parser.add_argument('--points', type=str,
                        help='A path to a csv file, or folder containing '
                             'multiple csv files. Each csv file should '
                             'contain following: name, row, column')

    parser.add_argument('--prefix', type=str, default="",
                        help='A prefix that all images of interest have in common to '
                             'narrow the search space, else leave blank')

    parser.add_argument('--source_id_1', type=str, required=True,
                        help='The ID of the Source containing images.')

    parser.add_argument('--source_id_2', type=str, default=None,
                        help='The ID of the Source containing the model to use, if different.')

    parser.add_argument('--output_dir', type=str, required=True,
                        help='A root directory where all predictions will be '
                             'saved to.')

    args = parser.parse_args()

    try:
        # Call the api function
        api(args)
        print("Done.\n")

    except Exception as e:
        print(f"ERROR: {e}")
        print(traceback.format_exc())


if __name__ == "__main__":
    main()