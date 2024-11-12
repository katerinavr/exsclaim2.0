from exsclaim import journal
from exsclaim import pipeline
from exsclaim import tool
from exsclaim.pipeline import Pipeline

test_json =  {
    "name": "html-ECPs",

    "pdf_folder": "pdf_files" ,

     "llm": "gpt-3.5-turbo",

    "openai_API": YOUR_OPENAI_API ,
    "save_format": ["boxes", "save_subfigures", "csv"],

    "logging": ["print", "exsclaim.log"]
    }
test_pipeline = Pipeline(test_json)#'./query/nature-ESEM.json')
results = test_pipeline.run(caption_distributor=True,
        journal_scraper=False, figure_separator=True, pdf_scraper=True)
