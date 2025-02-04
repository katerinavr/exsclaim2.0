from exsclaim.pipeline import Pipeline


test_json =  {

    "name": "nature-nano",

    "journal_family": "nature",

    "maximum_scraped": 3,

    "sortby": 'relevant',

    "llm": "gpt-4o",

    "openai_API": YOUR_OPENAI_API_KEY ,

    "query":

    { "search_field_1":

        {   "term":"Ag nanoparticle",

            "synonyms":["Ag nanoparticles", "silver nanoparticle", "silver nanoparticle", "nanoparticles of silver", "AgNPs", "AgNP", "Ag NPs", "silver NPs", "silver NP"] } },

    "open": True,

    "save_format": ["boxes", "save_subfigures" ],

    "logging": ["print", "exsclaim.log"]
    }

test_pipeline = Pipeline(test_json)#'./query/nature-ESEM.json')
results = test_pipeline.run(caption_distributor=True,
        journal_scraper=True, figure_separator=True, pdf_scraper=False)
