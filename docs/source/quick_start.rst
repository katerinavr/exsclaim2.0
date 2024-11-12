Quick Start Guide
=================

This guide will help you quickly get started with using exsclaim 2.0.

1. **Install the Project**

   Follow the instructions in the :doc:`installation` guide to set up your environment.

2. **Configure `query.json`**

   Before running the application, you need to configure the `query.json` file with your custom settings.

   **Example Configuration of `query.json`**:

   Below is an example configuration of `query.json`, which serves as the input to the pipeline. You can find additional example queries under `/exsclaim/query`.

   .. code-block:: json

      {
          "name": "nature_ESEM",
          "journal_family": "nature",
          "maximum_scraped": 500,
          "sortby": "relevant",
          "query": {
              "search_field_1": {
                  "term": "ESEM",
                  "synonyms": ["Environmental SEM", "Environmental Scanning Electron Microscope"]
              }
          },
          "llm": "gpt-3.5-turbo",
          "openai_API": "your_openai_api_key_here",
          "context_retrieval": true,
          "materials_ner": true,
          "open": false,
          "save_format": ["boxes", "save_subfigures", "csv"],
          "logging": ["print", "exsclaim.log"]
      }

   **Notes**:

   - Replace `"your_openai_api_key_here"` with your actual OpenAI API key.
   
   **Description of fields**:

     - **`name`**: The name of the folder where the files will be saved.
     - **`journal_family`**: Choose from `Nature`, `ACS`, `RSC`, or `Wiley`.
     - **`maximum_scraped`**: Define the number of papers to scrape data from.
     - **`query`**: Specify search terms and their synonyms.
     - **`open`**: Indicates if the articles are open access.
     - **`save_format`**: Options for saving output:
       - `"boxes"`: Draw bounding boxes.
       - `"visualization"`: Save subfigures with their labels.
       - `"csv"`: Save extracted data in CSV format.
     - **`logging`**: Options for logging events (e.g., `"print"` to display events).

3. **Using the HTMLScraper and PDFScraper**

   When using the `HTMLScraper` or the `PDFScraper`, you need to create a folder (`my_files`) and upload your HTML/PDF files. Then, update the folder location in `query.json` as shown below:

   **Example Configuration for HTMLScraper**:

   .. code-block:: json

      {
          "name": "html-tem",
          "html_folder": "my_files",
          "llm": "gpt-3.5-turbo",
          "openai_API": "your_openai_api_key_here",
          "save_format": ["boxes", "save_subfigures", "csv"],
          "logging": ["print", "exsclaim.log"]
      }

   Follow examples 2 and 3 to scrape multimodal data using your selected literature papers.

4. **Additional Setup**

   Some parts of the project may require additional setup, such as environment variables or database configurations.

   - **Environment Variables**: Create a `.env` file in the root directory and add any required environment variables as shown below:

     **Example .env file**:

     .. code-block:: text

        OPENAI_API_KEY=your_openai_api_key_here
        HUGGINGFACE_API_TOKEN=your_hf_token_here

5. **Launch the Application**

   After configuring everything, start the application with the following commands:

   .. code-block:: bash

      # Load necessary models
      python load_models.py

   .. code-block:: bash

      # Run the main application
      python run_exsclaim.py

If you encounter any issues, please contact the maintainers.
