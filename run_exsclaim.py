from exsclaim.pipeline import Pipeline

test_json =  {
    "name": "html-ECPs",

    "pdf_folder": "pdf_files" ,

     "llm": "gpt-4o",

    "openai_API": YOUR_OPENAI_API ,
    "save_format": ["boxes", "save_subfigures", "csv"],

    "logging": ["print", "exsclaim.log"]
    }
test_pipeline = Pipeline(test_json)#'./query/nature-ESEM.json')
results = test_pipeline.run(caption_distributor=True,
        journal_scraper=True, figure_separator=True, pdf_scraper=False)