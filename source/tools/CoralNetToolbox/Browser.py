import os
import sys
import time
import json
import requests
from bs4 import BeautifulSoup

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager

from Common import LOGIN_URL
from Common import CORALNET_URL


# -------------------------------------------------------------------------------------------------
# Functions to authenticate with CoralNet
# -------------------------------------------------------------------------------------------------


def authenticate(username, password):
    """
    Authenticate with CoralNet; used to make sure user has the correct credentials.
    """

    print("\n###############################################")
    print("Authentication")
    print("###############################################\n")
    print(f"NOTE: Authenticating user {username}")

    try:
        # Send a GET request to the login page to retrieve the login form
        response = requests.get(LOGIN_URL, timeout=30)

    except Exception as e:
        raise Exception(f"ERROR: CoralNet timed out after 30 seconds.\n{e}")

    # Pass along the cookies
    cookies = response.cookies

    # Parse the HTML of the response using BeautifulSoup
    soup = BeautifulSoup(response.text, "html.parser")

    # Extract the CSRF token from the HTML of the login page
    csrf_token = soup.find("input", attrs={"name": "csrfmiddlewaretoken"})

    # Create a dictionary with the login form fields and their values
    # (replace "username" and "password" with your actual username and
    # password)
    data = {
        "username": username,
        "password": password,
        "csrfmiddlewaretoken": csrf_token["value"],
    }

    # Include the "Referer" header in the request
    headers = {
        "Referer": LOGIN_URL,
    }

    # Use requests.Session to create a session that will maintain your login
    # state
    with requests.Session() as session:

        # Use session.post() to submit the login form, including the
        # "Referer" header
        response = session.post(LOGIN_URL,
                                data=data,
                                headers=headers,
                                cookies=cookies)

        if "credentials you entered did not match" in response.text:
            raise Exception(f"ERROR: Authentication unsuccessful for '{username}'\n "
                            f"Please check that your usename and password are correct")
        else:
            print(f"NOTE: Authentication successful for {username}")


def check_for_browsers(headless):
    """
    Check if Chrome browser is installed.
    """

    print("\n###############################################")
    print("Browser")
    print("###############################################\n")

    options = Options()
    # Silence, please.
    options.add_argument("--log-level=3")

    if headless:
        # Add headless argument
        options.add_argument('headless')
        # Needed to avoid timeouts when running in headless mode
        options.add_experimental_option('extensionLoadTimeout', 3600000)

    try:
        # Check if ChromeDriver path is already in PATH
        chrome_driver_path = "chromedriver.exe"  # Adjust the name if needed
        if not any(
            os.path.exists(os.path.join(directory, chrome_driver_path))
            for directory in os.environ["PATH"].split(os.pathsep)
        ):
            # If it's not in PATH, attempt to install it
            chrome_driver_path = ChromeDriverManager().install()

            if not chrome_driver_path:
                raise Exception("ERROR: ChromeDriver installation failed.")
            else:
                # Add the ChromeDriver directory to the PATH environment variable
                os.environ["PATH"] += os.pathsep + os.path.dirname(chrome_driver_path)
                print("NOTE: ChromeDriver added to PATH")

        # Attempt to open a browser
        browser = webdriver.Chrome(options=options)

        print("NOTE: Using Google Chrome")
        return browser

    except Exception as e:
        print(f"WARNING: Google Chrome could not be used\n{e}")

    print("ERROR: Issue with getting browser. Exiting")
    sys.exit(1)


def login(driver):
    """
    Log in to CoralNet using Selenium.
    """

    print("\n###############################################")
    print("Login")
    print("###############################################\n")

    # Create a variable for success
    success = False

    # Navigate to the page to login
    driver.get(CORALNET_URL + "/accounts/login/")

    # Find the username button
    path = "id_username"
    username_input = WebDriverWait(driver, 10).until(
        EC.presence_of_element_located((By.ID, path)))

    # Find the password button
    path = "id_password"
    password_input = WebDriverWait(driver, 10).until(
        EC.presence_of_element_located((By.ID, path)))

    # Find the login button
    path = "//input[@type='submit'][@value='Sign in']"
    login_button = WebDriverWait(driver, 10).until(
        EC.presence_of_element_located((By.XPATH, path)))

    # Enter the username and password
    username_input.send_keys(driver.capabilities['credentials']['username'])
    password_input.send_keys(driver.capabilities['credentials']['password'])

    # Click the login button
    time.sleep(3)
    login_button.click()

    # Confirm login was successful; after 60 seconds, throw an error.
    try:
        path = "//button[text()='Sign out']"

        WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.XPATH, path)))

        # Login was successful
        success = True

        print(f"NOTE: Successfully logged in for {driver.capabilities['credentials']['username']}")

    except Exception as e:
        raise ValueError(f"ERROR: Could not login with "
                         f"{driver.capabilities['credentials']['username']}\n{e}")

    return driver, success


def check_permissions(driver):
    """
    Check if the user has permission to access the page.
    """

    try:
        # First check that this is existing source the user has access to
        path = "content-container"
        status = WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.ID, path)))

        # Check the status
        if not status.text:
            raise Exception(f"ERROR: Unable to access page information")

    except Exception as e:
        print(f"ERROR: {e} Exiting.")
        sys.exit(1)

    return driver, status


def get_token(username, password):
    """
    Retrieves a CoralNet authentication token for API requests.
    """
    # Requirements for authentication
    CORALNET_AUTH = CORALNET_URL + "/api/token_auth/"
    HEADERS = {"Content-type": "application/vnd.api+json"}
    PAYLOAD = {"username": username, "password": password}

    try:

        # Response from CoralNet when provided credentials
        response = requests.post(CORALNET_AUTH,
                                 data=json.dumps(PAYLOAD),
                                 headers=HEADERS,
                                 timeout=10)
    except Exception as e:
        raise Exception(f"ERROR: {e}")

    if response.ok:

        print("NOTE: API token retrieved successfully")

        # Get the coralnet token returned to the user
        CORALNET_TOKEN = json.loads(response.content.decode())['token']

        # Update the header to contain the user's coralnet token
        HEADERS = {"Authorization": f"Token {CORALNET_TOKEN}",
                   "Content-type": "application/vnd.api+json"}

    else:
        raise ValueError(f"ERROR: Could not retrieve API token\n{response.content}")

    return CORALNET_TOKEN, HEADERS