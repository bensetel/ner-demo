import re


def is_atl_writer(name: str) -> bool:
    atl_writers = [
        'Staci Zaretsky',
        'Joe Patrice',
        'Kathryn Rubino',
        'John Lerner',
        'Brian Dalton',
        'Chris Williams',
        "Zach Warren",
        "David Lat",
        "Lauren E. Skerrett",
        "Elie Mystal",

    ]
    name = name.lower()
    results = [person for person in atl_writers if ((name in person.lower()) or (person.lower() in name))]
    return (len(results)!=0)

def is_name(name: str) -> bool: #TODO - support unicode names
    if not(bool(re.fullmatch("([\w\-\' ]{2,15}){2,4}", name.strip()))):
           return False
           
    if not(bool(bool(re.search("(\w* \w*){1,4}", name.strip())))):
           return False
    if False in [x[0].isupper() for x in name.split(' ') if x != '']:
           return False
    else:
           return True

def has_bad_keyword(text: str) -> bool:
    bad_keywords = [
        "Here",
        "Is",
        "Was",
        "Are",
        "Were",
        "No",
        "Not",
        "Specific",
        "Specified",
        "Mention",
        "Magic",
        "Circle",
        "Law360",
        "Above",
        "Slappo", #seeming hallucination
        "The",
        "At",
        "Associate",
        "Associates",
        "Summer",
        "Summers",
        "Team",
        "Biglaw",
        "Big law",
        "Partner",
        "Partners",
        "Anonymous",
        "Unknown",
        "Counsel",
        "None",
        "CEO",
        "Am Law",
        "Entity",
        "Entities",
        "Chair",
        "Founder",
        "House",
        "Lawyer",
        "Lawyers",
        "Student",
        "Students",
        "Employee",
        "Employees",
        "Manage",
        "Manager",
        "Managing",
        "Management",
        "Staff",
        "Staffer",
        "Staffers",
        "Multiple",
        "Unnamed",
        "Spokesperson",
        "Business",
        "Support",
        "Biller",
        "Billers",
        "Scale", #advertiser
        "LexisNexis",
        "Thomson Reuters",
        'Law firm',
        'Office',
        "ATL",
        "Pilot", #advertiser
        '(',
        '[',
        '*',
        ":"]
    is_bad = False
    for keyword in bad_keywords:
        if (keyword.lower() + ' ' in text.lower()) or (' ' + keyword.lower() in text.lower()) or (keyword.lower() == text.lower()) or (bool(re.match('.*[0-9].*', text))): #TODO - rewrite to match full words better
            is_bad = True
    if is_atl_writer(text):
        is_bad = True
    return is_bad




def remove_word(word: str, sentence: str) -> str:
    idx = sentence.index(word)
    sentence = sentence[:idx] + sentence[idx+len(word):]
    return sentence
