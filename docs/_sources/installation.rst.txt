Installation Guide
==================

This document provides instructions on how to set up and install the project.

Prerequisites
-------------

Before installing, make sure you have the following installed:

- Python 3.11
- Git
- openai

### Clone the Repository

First, clone the repository to your local machine:

.. code-block:: bash

   git clone https://github.com/katerinavr/exsclaim2.0.git
   cd exsclaim2.0

Setting Up a Virtual Environment
--------------------------------

It's recommended to use a virtual environment to manage dependencies. Here’s how to create and activate one:

.. code-block:: bash

   # On Windows
   python -m venv env
   env\Scripts\activate

   # On macOS or Linux
   python3 -m venv env
   source env/bin/activate

Install Dependencies
--------------------

Once in your virtual environment, install the required dependencies:

.. code-block:: bash

   pip install -r requirements.txt

### Conda Alternative

If you’re using Conda, you can create an environment with:

.. code-block:: bash

   conda env create -f environment.yml
   conda activate your-env-name

Additional Setup
----------------

Some parts of the project may require additional setup, such as environment variables or database configurations.

- **Environment Variables**: Create a `.env` file in the root directory and add any required environment variables as shown below:

  .. code-block:: text

     # Example .env file
     API_KEY=your_api_key_here


Start the application with:

.. code-block:: bash

   python run_exsclaim.py

If you encounter any issues, refer to the Troubleshooting section or contact the maintainers.
