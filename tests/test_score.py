"""Unit tests for code/score.py. Run: python tests/test_score.py"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "code"))
from score import score_one  # noqa: E402

TWAIN = {"answer_type": "entity", "gold_answer": "Mark Twain", "gold_variants": ["Mark Twain", "मार्क ट्वैन"]}
ORWELL = {"answer_type": "year", "gold_answer": "1950", "gold_variants": ["1950"]}
HEMINGWAY = {"answer_type": "entity", "gold_answer": "Ernest Hemingway", "gold_variants": ["अर्नेस्ट हेमिंग्वे"]}
DENVER = {"answer_type": "entity", "gold_answer": "Denver", "gold_variants": ["डेनवर"]}
FELLOWSHIP = {"answer_type": "entity", "gold_answer": "The Fellowship of the Ring",
              "gold_variants": ["द फ़ेलोशिप ऑफ़ द रिंग"]}
SEATS = {"answer_type": "number", "gold_answer": "48", "gold_variants": ["48", "forty-eight", "४८", "अड़तालीस"]}
TILAK = {"answer_type": "entity", "gold_answer": "Bal Gangadhar Tilak",
         "gold_variants": ["Tilak", "Lokmanya Tilak", "बाल गंगाधर तिलक", "तिलक"]}
BJP = {"answer_type": "entity", "gold_answer": "Bharatiya Janata Party", "gold_variants": ["BJP", "भाजपा"]}
SECOND = {"answer_type": "number", "gold_answer": "2nd", "gold_variants": ["second", "2nd", "2", "दूसरा", "दूसरे"]}
NILE = {"answer_type": "entity", "gold_answer": "Nile", "gold_variants": ["नील"]}

CASES = [
    # (item, response, expected)
    (TWAIN, "Mark Twain", True),
    (TWAIN, "मार्क ट्वेन", True),            # spelling differs from gold Devanagari -> transliteration + fuzzy
    (TWAIN, "Answer: **Mark Twain**", True),
    (TWAIN, "Ernest Hemingway", False),
    (ORWELL, "1950", True),
    (ORWELL, "George Orwell ki mrityu 1950 mein hui thi.", True),
    (ORWELL, "१९५०", True),
    (ORWELL, "21 January 1950", True),
    (ORWELL, "1949", False),
    (ORWELL, "I don't know.", False),
    (HEMINGWAY, "Hemingway", True),
    (HEMINGWAY, "अर्नेस्ट हेमिंग्वे", True),
    (HEMINGWAY, "Ernest Rutherford", False),
    (DENVER, "Denver, Colorado", True),
    (DENVER, "डेनवर", True),
    (DENVER, "Boulder", False),
    (FELLOWSHIP, "The Fellowship of the Ring", True),
    (FELLOWSHIP, "The Return of the King", False),
    (FELLOWSHIP, "The Two Towers", False),
    (SEATS, "48 seats", True),
    (SEATS, "४८", True),
    (SEATS, "80", False),
    (TILAK, "Lokmanya Tilak", True),
    (TILAK, "बाल गंगाधर तिलक", True),
    (TILAK, "Mahatma Gandhi", False),
    (BJP, "BJP", True),
    (BJP, "भारतीय जनता पार्टी (भाजपा)", True),
    (BJP, "Congress", False),
    (SECOND, "India ranks second.", True),
    (SECOND, "दूसरा", True),
    (SECOND, "First", False),
    (NILE, "The Nile River", True),
    (NILE, "नील नदी", True),
    (NILE, "Amazon", False),
    (TWAIN, "", False),
    # near misses that must stay wrong
    (HEMINGWAY, "अर्नेस्ट रदरफोर्ड", False),
    (TILAK, "बाल ठाकरे", False),
    ({"answer_type": "entity", "gold_answer": "Jawaharlal Nehru", "gold_variants": ["जवाहरलाल नेहरू"]}, "Motilal Nehru", False),
    ({"answer_type": "entity", "gold_answer": "Jawaharlal Nehru", "gold_variants": ["जवाहरलाल नेहरू"]}, "मोतीलाल नेहरू", False),
    ({"answer_type": "entity", "gold_answer": "Jawaharlal Nehru", "gold_variants": ["जवाहरलाल नेहरू"]}, "Nehru", True),
    ({"answer_type": "entity", "gold_answer": "Rajasthan", "gold_variants": ["राजस्थान"]}, "राज्यसभा", False),
    (HEMINGWAY, "Hemingway ne suicide kiya tha", True),
    # Devanagari transliteration variants found in real model output (review 2026-10-26)
    ({"answer_type": "entity", "gold_answer": "James Madison", "gold_variants": ["जेम्स मैडिसन"]}, "जेम्स मेडिसन।", True),
    ({"answer_type": "entity", "gold_answer": "Hillary Clinton", "gold_variants": ["हिलरी क्लिंटन"]},
     "हिलेरी क्लिंटन, न्यूयॉर्क, संयुक्त राज्य अमेरिका की पूर्व प", True),
    ({"answer_type": "entity", "gold_answer": "Nuremberg", "gold_variants": ["नूर्नबर्ग"]}, "न्यूरेमबर्ग, जर्मनी", True),
    ({"answer_type": "entity", "gold_answer": "Rutherford B. Hayes", "gold_variants": ["रदरफोर्ड बी. हेस"]}, "राथेरफोर्ड बी. हेस", True),
    ({"answer_type": "entity", "gold_answer": "Rocky Mountains", "gold_variants": ["रॉकी पर्वत"]}, "रॉकी पर्वत श्रंखला", True),
    ({"answer_type": "entity", "gold_answer": "Ivan IV Vasilyevich", "gold_variants": ["इवान चतुर्थ"]}, "Ivan IV", True),
    ({"answer_type": "entity", "gold_answer": "New York City", "gold_variants": ["न्यूयॉर्क शहर"]}, "New York", True),
    ({"answer_type": "entity", "gold_answer": "Mississippi River", "gold_variants": ["मिसिसिपी नदी"]}, "Mississippi", True),
    ({"answer_type": "entity", "gold_answer": "Wright brothers", "gold_variants": ["राइट बंधु"]}, "Wright", True),
    ({"answer_type": "entity", "gold_answer": "Beyoncé", "gold_variants": ["बेयोंसे"]}, "बियोन्से।", True),
    ({"answer_type": "entity", "en": "What is the third book in the Harry Potter series?",
      "gold_answer": "Harry Potter and the Prisoner of Azkaban", "gold_variants": []}, "Prisoner of Azkaban", True),
    ({"answer_type": "entity", "en": "What is the longest Harry Potter book?",
      "gold_answer": "Harry Potter and the Order of the Phoenix", "gold_variants": []}, "Harry Potter.", False),
    ({"answer_type": "entity", "en": "Which Article of the Constitution deals with the election of the President of India?",
      "gold_answer": "Article 54", "gold_variants": ["54", "अनुच्छेद 54"]}, "Article 55.", False),
    ({"answer_type": "entity", "gold_answer": "Baji Rao II", "gold_variants": ["बाजी राव द्वितीय"]}, "bajirao I", False),
    ({"answer_type": "entity", "gold_answer": "Henry VIII of England", "gold_variants": ["हेनरी अष्टम"]},
     "King Charles II of England had the most marriages", False),
    ({"answer_type": "entity", "gold_answer": "Santa Barbara", "gold_variants": ["सांता बारबरा"]}, "California", False),
    ({"answer_type": "entity", "en": "What is the first Star Wars movie?",
      "gold_answer": "Star Wars: Episode IV – A New Hope", "gold_variants": []}, "A New Hope", True),
    ({"answer_type": "entity", "en": "What is the first Star Wars movie?",
      "gold_answer": "Star Wars: Episode IV – A New Hope", "gold_variants": []}, "Star Wars.", False),
    ({"answer_type": "entity", "gold_answer": "Boston Red Sox", "gold_variants": []}, "Red Sox", True),
    ({"answer_type": "number", "en": "Which Article of the Constitution deals with the election of the President of India?",
      "gold_answer": "Article 54", "gold_variants": ["54", "Article 54", "अनुच्छेद 54"]},
     "भारत के राष्ट्रपति के चुनाव से संबंधित अनुच्छेद 55 है।", False),
    ({"answer_type": "entity", "en": "Who established the Bahmani Sultanate?", "gold_answer": "Ala-ud-Din Bahman Shah",
      "gold_variants": ["Alauddin Bahman Shah", "Bahman Shah", "अलाउद्दीन बहमन शाह"]},
     "हमायूं के दामाद जलालुद्दीन फिरोज़ खिलजी ने बहमनी सल्तनत की स्थापना की।", False),
    # wrong answers the old fuzzy rule accepted
    ({"answer_type": "entity", "gold_answer": "Super Nintendo Entertainment System", "gold_variants": ["सुपर निंटेंडो"]},
     "Nintendo Entertainment System (NES)", False),
    ({"answer_type": "entity", "gold_answer": "Super Nintendo Entertainment System", "gold_variants": ["सुपर निंटेंडो"]},
     "Super Nintendo.", True),
    ({"answer_type": "entity", "gold_answer": "Mixed economy", "gold_variants": ["mixed", "मिश्रित अर्थव्यवस्था"]},
     "Economy of India is primarily service-based.", False),
    ({"answer_type": "entity", "gold_answer": "Mars", "gold_variants": ["मंगल"]}, "Mercury", False),
    ({"answer_type": "entity", "gold_answer": "Boston Red Sox", "gold_variants": ["बोस्टन रेड सॉक्स"]}, "Boston Celtics", False),
]


def main():
    fails = 0
    for item, resp, exp in CASES:
        got, rule = score_one(item, resp)
        if got != exp:
            fails += 1
            print(f"FAIL  {item['gold_answer']!r:30} {resp!r:45} expected {exp} got {got} ({rule})")
    print(f"{len(CASES) - fails}/{len(CASES)} passed")
    sys.exit(1 if fails else 0)


if __name__ == "__main__":
    main()
