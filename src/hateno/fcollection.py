#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from .errors import *

class FCollection():
    '''
    Represent a collection of functions, with possible categories.

    Parameters
    ----------
    categories : list
        Names of the categories to use.
    '''

    def __init__(self, *, categories = []):
        self._list = {}
        self._use_categories = bool(categories)

        if categories:
            self._list = {cat: {} for cat in categories}

    def set(self, fname, f, *, category = None):
        '''
        Add a function to the collection, or replace an existing one.

        Parameters
        ----------
        fname : str
            Name of the function.

        f : function
            Function to store.

        category : str
            Name of the category, if any.
        '''

        try:
            list_to_manage = self._list[category] if self._use_categories else self._list

        except KeyError:
            raise FCollectionCategoryNotFoundError(category)

        else:
            list_to_manage[fname] = f

    def delete(self, fname, *, category = None):
        '''
        Delete a function.

        Parameters
        ----------
        fname : str
            Name of the function to delete.

        category : str
            Name of the category, if any.
        '''

        try:
            list_to_manage = self._list[category] if self._use_categories else self._list

        except KeyError:
            raise FCollectionCategoryNotFoundError(category)

        else:
            try:
                del list_to_manage[fname]

            except KeyError:
                raise FCollectionFunctionNotFoundError(fname)
