Installation Guide
==================

This document provides instructions on how to set up and install the project.

Prerequisites
-------------

Before installing, make sure you have the following installed:

- Python 3.11
- Git
- openai

Clone the Repository
--------------------

First, clone the repository to your local machine:

.. code-block:: bash

   git clone https://github.com/katerinavr/exsclaim2.0.git
   cd exsclaim2.0

Setting Up a Virtual Environment
--------------------------------

It's recommended to use a virtual environment to manage dependencies. Here’s how to create and activate one:

.. code-block:: bash

   # On Windows
   python -m venv excslaim2
   excslaim2\Scripts\activate

   # On macOS or Linux
   python3 -m venv excslaim2
   source excslaim2/bin/activate


Install Dependencies
--------------------

Once in your virtual environment, install the required dependencies:

.. code-block:: bash

   pip install -r requirements.txt