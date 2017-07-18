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
                "lines": [
                    "first line", // plain text that will be displayed
                    "second line {foo}" // displays: second line bar
                ],
                "vars": { // defines local variables
                    "foo": "bar"
                },
                "pid": "start" // the id for the page (used as prefix in the result file)
                "continue": "next", // creates a single button at the bottom -- default ("next") can be omitted
                "type": "plain" // the type of page -- default ("plain") can be omitted
            }, {
                "type": "each", // repeats a sequence of pages
                "name": "ix", // the iteration variable name -- it can be used via {ix} in fields
                "vars": { // defines local variables
                    "img_len": 25 // we define the range as variable so we can use it in the text
                },
                "to": "{img_len}", // iterate until this number
                "pages": [
                    // ... pages to repeat ...
                    {
                        "lines": [
                            "image {ix} / {img_len}", // displays: image 0 / 25
                            [ "img", "path/to/image{ix}.png", "" ] // the image to display
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
                "lines": [
                    // other special lines
                    // [ question_type, display_text, question_id ]
                    [ "text", "just text", "" ], // simple text -- equivalent to "just text"
                    [ "likert", "fun", "fun" ], // likert scale
                    [ "likert", "confidence", "conf" ]
                ],
                "pid": "specials"
            }, {
                "lines": [
                    "Thanks! {_token}" // _token is a special variable containing the user id
                ],
                "continue": "end", // indicates the end of the survey -- this page must exist
                "pid": "end"
            }
        ]
    }

Each user creates a result file with its unique token in the output folder.
The result file is a JSON file containing all answers.
