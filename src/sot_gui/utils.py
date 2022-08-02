from typing import Dict, List, Any


def quoted(string: str) -> str:
    """ Returns a string wrapped in escaped double quotes.

    Args:
        string: The string to wrap.
    """
    return f"\"{string}\""


def get_dict_with_element(dict_list: List[Dict], key: Any, value: Any) -> Dict:
    """ Returns the first dictionary whose key/value pair corresponds
        to the given arguments, or None if none was found.

        Args:
            dict_list: The list of dictionaries to search.
            key: The key whose corresponding value must be the `value` argument
                for a dictionary to be returned.
            value: The value required for the given `key`.

    """
    return (next((d for d in dict_list if d.get(key) == value), None))


def get_dict_with_element_in_list(dict_list: List[Dict], key: Any,
                                  values: List) -> Dict:
    """ Returns the first dictionary those whose `key` corresponds to one
        of the given `values`, or None if none was found.

        Args:
            dict_list: The list of dictionaries to search.
            key: The key whose corresponding value must be an element of the
                `values` argument for a dictionary to be returned.
            values: List of accepted values for the given `key`.
    """
    for value in values:
        found_dict = get_dict_with_element(dict_list, key, value)
        if found_dict is not None:
            return found_dict
    return None


def get_dicts_with_element(dict_list: List[Dict], key: Any, value: Any) \
                           -> List[Dict]:
    """ Filters the dictionaries and returns those whose key/value pair
        corresponds to the given arguments.

        Args:
            dict_list: The list of dictionaries to search.
            key: The key whose corresponding value must be the `value` argument
                for a dictionary to be returned.
            value: The value required for the given `key`.
    """
    return [d for d in dict_list if d.get(key) == value]


def get_dicts_with_element_in_list(dict_list: List[Dict], key: Any,
                                   values: List) -> List[Dict]:
    """ Filters the dictionaries and returns only those whose `key` corresponds
        to one of the given `values`.

        Args:
            dict_list: The list of dictionaries to search.
            key: The key whose corresponding value must be an element of the
                `values` argument for a dictionary to be returned.
            values: List of accepted values for the given `key`.
    """
    all_filtered_dicts = []

    for value in values:
        all_filtered_dicts += get_dicts_with_element(dict_list, key, value)

    return all_filtered_dicts
