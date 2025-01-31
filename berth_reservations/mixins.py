class ChoicesMixin:
    """
    Backward compatibility mixin for Django 4.2 enums.
    """
    def __repr__(self):
        """
        Use value when cast to str, so that Choices represents itself 
        as they did earlier before upgrading Django from 3.2 to 4.2.
        Example, 
        when calling `PeriodType.YEAR` instead of returning `
        `PeriodType.YEAR`, like this
        ```
        In [1]: from payments.enums import PeriodType
        In [2]: PeriodType.YEAR
        Out[2]: PeriodType.YEAR
        ```
        it should return the value, like it did earlier
        ```
        In [1]: from payments.enums import PeriodType
        In [2]: PeriodType.YEAR
        Out[2]: 'year'
        ```

        NOTE: implementation is directly copied from `django.db.models.enums.Choices.__str__`.
        """
        return str(self.value)