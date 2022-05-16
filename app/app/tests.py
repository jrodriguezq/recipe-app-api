""" Sample tests """


from django.test import SimpleTestCase

from app import calc


class CalcTest(SimpleTestCase):
    """ Test the calc module """

    def test_add_numbers(self):
        """ Test add function """
        res = calc.add(5, 4)

        self.assertEqual(res, 9)

    def test_substract_numbers(self):
        """ Test substract function """
        res = calc.substract(10, 15)

        self.assertEqual(res, -5)
