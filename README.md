# Jeopardy Flask API

This repository contains a Python Flask backend API for the Jeopardy React web application (https://github.com/truongtrain/jeopardy-react).
The API acts as a web scraper and data service, retrieving real game data from the Jeopardy archives based on a game ID provided by the frontend.
The scraped data is normalised and returned as structured JSON, which the React app uses to render full Jeopardy-style gameplay.

Example Response:

    [
      [
        {
            "category": "NAMELESS IN SHAKESPEARE",
            "category_note": "",
            "clue_id": "535723",
            "daily_double_wager": 0,
            "number": 30,
            "response": {
                "correct_contestant": "Erin",
                "correct_response": "the Fool",
                "incorrect_contestants": [],
                "incorrect_responses": []
            },
            "text": "THIS IRREVERENT CHARACTER TELLS KING LEAR \"THOU HADST LITTLE WIT IN THY BALD CROWN WHEN THOU GAV'ST THY GOLDEN ONE AWAY\"",
            "url": "",
            "value": 200
        },
      ],
    ]
    
