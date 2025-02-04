<<<<<<< HEAD
=======
from exsclaim import journal
from exsclaim import pipeline
from exsclaim import tool
>>>>>>> ad843cee0eb4e59ae1bc9cb0b4ed08b64a3370fa
from exsclaim.pipeline import Pipeline

test_json =  {
    "name": "html-ECPs",

    "pdf_folder": "pdf_files" ,

<<<<<<< HEAD
     "llm": "gpt-4o",
=======
     "llm": "gpt-3.5-turbo",
>>>>>>> ad843cee0eb4e59ae1bc9cb0b4ed08b64a3370fa

    "openai_API": YOUR_OPENAI_API ,
    "save_format": ["boxes", "save_subfigures", "csv"],

    "logging": ["print", "exsclaim.log"]
    }
test_pipeline = Pipeline(test_json)#'./query/nature-ESEM.json')
results = test_pipeline.run(caption_distributor=True,
<<<<<<< HEAD
        journal_scraper=True, figure_separator=True, pdf_scraper=False)
=======
        journal_scraper=False, figure_separator=True, pdf_scraper=True)
>>>>>>> ad843cee0eb4e59ae1bc9cb0b4ed08b64a3370fa
