# email_reader# Email Reader Application

- Flask-based email reader application that processes emails and provides an the most necessary mails. It supports integration with GitHub Actions for continuous integration (CI) and deployment (CD) to Heroku.

![Example run](./email_reader.gif)

## Features
- Fetches and processes the most useful emails from a specified account.
- Filtering emails and provides useful ones.
- Continuous Integration (CI) with GitHub Actions.
- Continuous Deployment (CD) to Heroku.
- Bilkent Experiment Mails (Paid + GE250/251)
- DAIS, AIRS mails coming from department personnel

## Prerequisites

To run this project locally or deploy it, you will need the following:

- **Python 3.8+**
- **pip** (Python package manager)
- A **Heroku** account for deployment.
- A **GitHub** account for managing CI/CD pipelines.

### Setting up the Environment

1. Clone the repository:

    ```bash
    git clone https://github.com/onurcangnc/email_reader.git
    ```

2. Navigate to the project directory:

    ```bash
    cd email_reader
    ```

3. Install the necessary dependencies:

    ```bash
    pip install -r requirements.txt
    ```

## Running the Application Locally

To run the application locally:

1. Start the Flask server:

    ```bash
    python app.py
    ```

2. Access the application in your web browser at:

    ```
    http://127.0.0.1:5000
    ```

## CI/CD Pipeline with GitHub Actions

- The project is integrated with GitHub Actions for continuous integration and continuous deployment.

### Continuous Integration

GitHub Actions will automatically run tests and linting checks whenever you push to the repository.

### Continuous Deployment to Heroku

- Upon pushing to the `main` branch, the GitHub Actions workflow will deploy the latest version of the application to Heroku.

- To enable deployment to Heroku, set up the following secrets in your GitHub repository settings:
- `HEROKU_API_KEY` - Your Heroku API key.
- `HEROKU_APP_NAME` - The name of your Heroku app.

## Deployment to Heroku

To manually deploy the app to Heroku, use the following steps:

1. Log in to Heroku using the CLI:

    ```bash
    heroku login
    ```

2. Create a new Heroku app:

    ```bash
    heroku create your-app-name
    ```

3. Push your application to Heroku:

    ```bash
    git push heroku main
    ```

4. Open the application:

    ```bash
    heroku open
    ```

## License

This project is licensed under the MIT License. See the `LICENSE` file for more details.
