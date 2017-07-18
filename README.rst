surveyengine
============

A customizable survey web user interface.

You can install *surveyengine* via

.. code:: bash

    pip install --user surveyengine

and run it via:

.. code:: bash

    python -m surveyengine spec.json output/

Where ``output`` is the output folder for the results and ``spec.json`` is a
survey specification:

.. code:: javascript

    {
        "title": "Survey Title Here", // the survey title
        "pages": [ // a sequence of pages
            {
                "type": "text", // a text page simply displays text
                "lines": [ // the text that will be displayed
                    "first line",
                    "second line"
                ],
                "continue": "next", // creates a single button at the bottom
                "pid": "start" // the id for the page (used as prefix in the result file)
            }, {
                "type": "each", // repeats a sequence of pages
                "name": "ix", // the iteration variable name -- it can be used via {ix} in fields
                "to": 25, // iterate until this number
                "pages": [
                    // ... pages to repeat ...
                    {
                        "type": "img", // an image page
                        "file": "path/to/image{ix}.png", // the image to display
                        "lines": [ // text displayed below the image
                            "please answer"
                        ],
                        "pid": "question:{ix}" // the id for the page
                        "continue": "choice", // creates a collection of buttons at the bottom
                        "values": [ // the values to choose from
                            "yes",
                            "no"
                        ]
                    }
                ]
                // this page type does not have a "continue" field
            }, {
                "type": "input", // multiple questions
                "lines": [
                    // [ question_id, display_text, question_type ]
                    [ "", "Just Text", "text" ], // simple text
                    [ "fun", "Fun", "likert" ], // likert scale
                    [ "conf", "Confidence", "likert" ]
                ],
                "continue": "next",
            }, {
                "type": "text",
                "lines": [
                    "Thanks!"
                ],
                "continue": "end", // indicates the end of the survey -- this page must exist
                "pid": "end"
            }
        ]
    }

Each user creates a result file with its unique token in the output folder.
The result file is a JSON file containing all answers.
