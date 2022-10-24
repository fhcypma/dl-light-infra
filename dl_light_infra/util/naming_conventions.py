"""
Helper functions to aid with naming conventions
"""
from re import finditer
from typing import List, Set


def delimited_str_split(delimited_str: str, delimiters: Set[str] = {"_", "-", "."}) -> List[str]:
    """Convert words and delimited words to list of words"""
    res = delimited_str
    for delimiter in delimiters:
        res = res.replace(delimiter, " ")
    return res.split(" ")

def camel_case_split(camel_case_str: str) -> List[str]:
    matches = finditer('.+?(?:(?<=[a-z])(?=[A-Z])|(?<=[A-Z])(?=[A-Z][a-z])|$)', camel_case_str)
    return [m.group(0) for m in matches]

def split(in_str) -> List[str]:
    "Split the string by delimiter _, - and . and by UpperCase. Then lower case it"
    list_of_lists = [camel_case_split(word) for word in delimited_str_split(in_str)]
    return [word.lower() for list in list_of_lists for word in list]

def to_upper_camel(in_str: str) -> str:
    """Delimited string to UpperCamelCase"""
    return "".join([word.capitalize() for word in split(in_str)])

def to_kebab(in_str: str) -> str:
    """Delimited string to kebab-notation"""
    return "-".join([word for word in split(in_str)])

def to_dot(in_str: str) -> str:
    """Delimited string to dot.notation"""
    return ".".join([word for word in split(in_str)])

def to_snake(in_str: str) -> str:
    """Delimited string to snake_notation"""
    return "_".join([word for word in split(in_str)])
