from unittest import TestCase
from sot_gui.dot_data_generator import DotDataGenerator

# To check if the dot code given as output is correct by displaying the
# graph: dreampuf.github.io/GraphvizOnline/

class TestHTMLRows(TestCase):
    """ Tests for the _get_html_rows_for_node method of the DotDataGenerator
        class.
    """

    def setUp(self):
        self._gen = DotDataGenerator()


    def test_equal_nb_in_out(self):
        """ Cases were the number of inputs is equal to the number of outputs.
        """

        # 1 input, 1 output:
        label = 'entity'
        inputs = ['sin0']
        outputs = ['sout0']
        expected_out = '\t\t<TR>\n' +\
            '\t\t\t<TD ROWSPAN="1" PORT="sin0">sin0</TD>\n' +\
            '\t\t\t<TD ROWSPAN="1">entity</TD>\n' +\
            '\t\t\t<TD ROWSPAN="1" PORT="sout0">sout0</TD>\n' +\
            '\t\t</TR>\n'
        actual_out = self._gen._get_html_rows_for_node(label, inputs, outputs)
        assert actual_out == expected_out

        # 2 inputs, 2 outputs:
        label = 'entity'
        inputs = ['sin0', 'sin1']
        outputs = ['sout0', 'sout1']
        expected_out = '\t\t<TR>\n' +\
            '\t\t\t<TD ROWSPAN="1" PORT="sin0">sin0</TD>\n' +\
            '\t\t\t<TD ROWSPAN="2">entity</TD>\n' +\
            '\t\t\t<TD ROWSPAN="1" PORT="sout0">sout0</TD>\n\t\t</TR>\n' +\
            '\t\t<TR>\n\t\t\t<TD ROWSPAN="1" PORT="sin1">sin1</TD>\n' +\
            '\t\t\t<TD ROWSPAN="1" PORT="sout1">sout1</TD>\n\t\t</TR>\n'
        actual_out = self._gen._get_html_rows_for_node(label, inputs, outputs)
        assert actual_out == expected_out

        # 4 inputs, 4 outputs:
        label = 'entity'
        inputs = ['sin0', 'sin1', 'sin2', 'sin3']
        outputs = ['sout0', 'sout1', 'sout2', 'sout3']
        expected_out = '\t\t<TR>\n' +\
            '\t\t\t<TD ROWSPAN="1" PORT="sin0">sin0</TD>\n' +\
            '\t\t\t<TD ROWSPAN="4">entity</TD>\n' +\
            '\t\t\t<TD ROWSPAN="1" PORT="sout0">sout0</TD>\n\t\t</TR>\n' +\
            '\t\t<TR>\n\t\t\t<TD ROWSPAN="1" PORT="sin1">sin1</TD>\n' +\
            '\t\t\t<TD ROWSPAN="1" PORT="sout1">sout1</TD>\n\t\t</TR>\n' +\
            '\t\t<TR>\n\t\t\t<TD ROWSPAN="1" PORT="sin2">sin2</TD>\n' +\
            '\t\t\t<TD ROWSPAN="1" PORT="sout2">sout2</TD>\n\t\t</TR>\n' +\
            '\t\t<TR>\n\t\t\t<TD ROWSPAN="1" PORT="sin3">sin3</TD>\n' +\
            '\t\t\t<TD ROWSPAN="1" PORT="sout3">sout3</TD>\n\t\t</TR>\n'
        actual_out = self._gen._get_html_rows_for_node(label, inputs, outputs)
        assert actual_out == expected_out


    def test_one_in_several_out(self):
        """ Cases were there is one input and several outputs. """

        # 1 input, 2 outputs
        label = 'entity'
        inputs = ['sin0']
        outputs = ['sout0', 'sout1']
        expected_out = '\t\t<TR>\n' +\
            '\t\t\t<TD ROWSPAN="2" PORT="sin0">sin0</TD>\n' +\
            '\t\t\t<TD ROWSPAN="2">entity</TD>\n' +\
            '\t\t\t<TD ROWSPAN="1" PORT="sout0">sout0</TD>\n\t\t</TR>\n' +\
            '\t\t<TR>\n\t\t\t<TD ROWSPAN="1" PORT="sout1">sout1</TD>\n' +\
            '\t\t</TR>\n'
        actual_out = self._gen._get_html_rows_for_node(label, inputs, outputs)
        assert actual_out == expected_out

        # 1 input, 3 outputs
        label = 'entity'
        inputs = ['sin0']
        outputs = ['sout0', 'sout1', 'sout2']
        expected_out = '\t\t<TR>\n' +\
            '\t\t\t<TD ROWSPAN="3" PORT="sin0">sin0</TD>\n' +\
            '\t\t\t<TD ROWSPAN="3">entity</TD>\n' +\
            '\t\t\t<TD ROWSPAN="1" PORT="sout0">sout0</TD>\n\t\t</TR>\n' +\
            '\t\t<TR>\n\t\t\t<TD ROWSPAN="1" PORT="sout1">sout1</TD>\n' +\
            '\t\t</TR>\n\t\t<TR>\n' +\
            '\t\t\t<TD ROWSPAN="1" PORT="sout2">sout2</TD>\n\t\t</TR>\n'
        actual_out = self._gen._get_html_rows_for_node(label, inputs, outputs)
        assert actual_out == expected_out


    def test_several_in_one_out(self):
        """ Cases were there is several inputs and one output. """

        # 2 inputs, 1 output
        label = 'entity'
        inputs = ['sin0', 'sin1']
        outputs = ['sout0']
        expected_out = '\t\t<TR>\n' +\
            '\t\t\t<TD ROWSPAN="1" PORT="sin0">sin0</TD>\n' +\
            '\t\t\t<TD ROWSPAN="2">entity</TD>\n' +\
            '\t\t\t<TD ROWSPAN="2" PORT="sout0">sout0</TD>\n\t\t</TR>\n' +\
            '\t\t<TR>\n\t\t\t<TD ROWSPAN="1" PORT="sin1">sin1</TD>\n' +\
            '\t\t</TR>\n'
        actual_out = self._gen._get_html_rows_for_node(label, inputs, outputs)
        assert actual_out == expected_out

        # 3 inputs, 1 output
        label = 'entity'
        inputs = ['sin0', 'sin1', 'sin2']
        outputs = ['sout0']
        expected_out = '\t\t<TR>\n' +\
            '\t\t\t<TD ROWSPAN="1" PORT="sin0">sin0</TD>\n' +\
            '\t\t\t<TD ROWSPAN="3">entity</TD>\n' +\
            '\t\t\t<TD ROWSPAN="3" PORT="sout0">sout0</TD>\n\t\t</TR>\n' +\
            '\t\t<TR>\n\t\t\t<TD ROWSPAN="1" PORT="sin1">sin1</TD>\n' +\
            '\t\t</TR>\n\t\t<TR>\n' +\
            '\t\t\t<TD ROWSPAN="1" PORT="sin2">sin2</TD>\n\t\t</TR>\n'
        actual_out = self._gen._get_html_rows_for_node(label, inputs, outputs)
        assert actual_out == expected_out


    def test_several_in_out_multiples(self):
        """ Cases were there are several inputs and outputs, and one of the
            numbers is a multiple of the other one.
        """

        # 2 inputs, 4 outputs
        label = 'entity'
        inputs = ['sin0', 'sin1']
        outputs = ['sout0', 'sout1', 'sout2', 'sout3']
        expected_out = '\t\t<TR>\n' +\
            '\t\t\t<TD ROWSPAN="2" PORT="sin0">sin0</TD>\n' +\
            '\t\t\t<TD ROWSPAN="4">entity</TD>\n' +\
            '\t\t\t<TD ROWSPAN="1" PORT="sout0">sout0</TD>\n\t\t</TR>\n' +\
            '\t\t<TR>\n\t\t\t<TD ROWSPAN="1" PORT="sout1">sout1</TD>\n' +\
            '\t\t</TR>\n\t\t<TR>\n' +\
            '\t\t\t<TD ROWSPAN="2" PORT="sin1">sin1</TD>\n' +\
            '\t\t\t<TD ROWSPAN="1" PORT="sout2">sout2</TD>\n\t\t</TR>\n' +\
            '\t\t<TR>\n\t\t\t<TD ROWSPAN="1" PORT="sout3">sout3</TD>\n' +\
            '\t\t</TR>\n'
        actual_out = self._gen._get_html_rows_for_node(label, inputs, outputs)
        assert actual_out == expected_out

        # 4 inputs, 2 outputs
        label = 'entity'
        inputs = ['sin0', 'sin1', 'sin2', 'sin3']
        outputs = ['sout0', 'sout1']
        expected_out = '\t\t<TR>\n' +\
            '\t\t\t<TD ROWSPAN="1" PORT="sin0">sin0</TD>\n' +\
            '\t\t\t<TD ROWSPAN="4">entity</TD>\n' +\
            '\t\t\t<TD ROWSPAN="2" PORT="sout0">sout0</TD>\n\t\t</TR>\n' +\
            '\t\t<TR>\n\t\t\t<TD ROWSPAN="1" PORT="sin1">sin1</TD>\n' +\
            '\t\t</TR>\n\t\t<TR>\n' +\
            '\t\t\t<TD ROWSPAN="1" PORT="sin2">sin2</TD>\n' +\
            '\t\t\t<TD ROWSPAN="2" PORT="sout1">sout1</TD>\n\t\t</TR>\n' +\
            '\t\t<TR>\n\t\t\t<TD ROWSPAN="1" PORT="sin3">sin3</TD>\n' +\
            '\t\t</TR>\n'
        actual_out = self._gen._get_html_rows_for_node(label, inputs, outputs)
        assert actual_out == expected_out


    def test_several_in_out_not_multiples(self):
        """ Cases were there are several inputs and outputs, and none of the
            numbers is a multiple of the other one.
        """

        # 2 inputs, 3 outputs
        label = 'entity'
        inputs = ['sin0', 'sin1']
        outputs = ['sout0', 'sout1', 'sout2']
        expected_out = '\t\t<TR>\n' +\
            '\t\t\t<TD ROWSPAN="1" PORT="sin0">sin0</TD>\n' +\
            '\t\t\t<TD ROWSPAN="3">entity</TD>\n' +\
            '\t\t\t<TD ROWSPAN="1" PORT="sout0">sout0</TD>\n\t\t</TR>\n' +\
            '\t\t<TR>\n\t\t\t<TD ROWSPAN="2" PORT="sin1">sin1</TD>\n' +\
            '\t\t\t<TD ROWSPAN="1" PORT="sout1">sout1</TD>\n\t\t</TR>\n' +\
            '\t\t<TR>\n\t\t\t<TD ROWSPAN="1" PORT="sout2">sout2</TD>\n' +\
            '\t\t</TR>\n'
        actual_out = self._gen._get_html_rows_for_node(label, inputs, outputs)
        assert actual_out == expected_out

        # 3 inputs, 2 outputs
        label = 'entity'
        inputs = ['sin0', 'sin1', 'sin2']
        outputs = ['sout0', 'sout1']
        expected_out = '\t\t<TR>\n' +\
            '\t\t\t<TD ROWSPAN="1" PORT="sin0">sin0</TD>\n' +\
            '\t\t\t<TD ROWSPAN="3">entity</TD>\n' +\
            '\t\t\t<TD ROWSPAN="1" PORT="sout0">sout0</TD>\n\t\t</TR>\n' +\
            '\t\t<TR>\n\t\t\t<TD ROWSPAN="1" PORT="sin1">sin1</TD>\n' +\
            '\t\t\t<TD ROWSPAN="2" PORT="sout1">sout1</TD>\n\t\t</TR>\n' +\
            '\t\t<TR>\n\t\t\t<TD ROWSPAN="1" PORT="sin2">sin2</TD>\n' +\
            '\t\t</TR>\n'
        actual_out = self._gen._get_html_rows_for_node(label, inputs, outputs)
        assert actual_out == expected_out


    def test_several_in_out_big_difference(self):
        """ Cases were there are several inputs and outputs, and the diffenrence
            between the two numbers is high.
        """

        # 2 inputs, 7 outputs
        label = 'entity'
        inputs = ['sin0', 'sin1']
        outputs = ['sout0', 'sout1', 'sout2', 'sout3', 'sout4', 'sout5',
                   'sout6']
        expected_out = '\t\t<TR>\n' +\
            '\t\t\t<TD ROWSPAN="3" PORT="sin0">sin0</TD>\n' +\
            '\t\t\t<TD ROWSPAN="7">entity</TD>\n' +\
            '\t\t\t<TD ROWSPAN="1" PORT="sout0">sout0</TD>\n\t\t</TR>\n' +\
            '\t\t<TR>\n\t\t\t<TD ROWSPAN="1" PORT="sout1">sout1</TD>\n' +\
            '\t\t</TR>\n\t\t<TR>\n' +\
            '\t\t\t<TD ROWSPAN="1" PORT="sout2">sout2</TD>\n\t\t</TR>\n' +\
            '\t\t<TR>\n\t\t\t<TD ROWSPAN="4" PORT="sin1">sin1</TD>\n' +\
            '\t\t\t<TD ROWSPAN="1" PORT="sout3">sout3</TD>\n\t\t</TR>\n' +\
            '\t\t<TR>\n\t\t\t<TD ROWSPAN="1" PORT="sout4">sout4</TD>\n' +\
            '\t\t</TR>\n\t\t<TR>\n' +\
            '\t\t\t<TD ROWSPAN="1" PORT="sout5">sout5</TD>\n\t\t</TR>\n' +\
            '\t\t<TR>\n\t\t\t<TD ROWSPAN="1" PORT="sout6">sout6</TD>\n' +\
            '\t\t</TR>\n'
        actual_out = self._gen._get_html_rows_for_node(label, inputs, outputs)
        assert actual_out == expected_out

        # 7 inputs, 2 outputs
        label = 'entity'
        inputs = ['sin0', 'sin1', 'sin2', 'sin3', 'sin4', 'sin5', 'sin6']
        outputs = ['sout0', 'sout1']
        expected_out = '\t\t<TR>\n' +\
            '\t\t\t<TD ROWSPAN="1" PORT="sin0">sin0</TD>\n' +\
            '\t\t\t<TD ROWSPAN="7">entity</TD>\n' +\
            '\t\t\t<TD ROWSPAN="3" PORT="sout0">sout0</TD>\n\t\t</TR>\n' +\
            '\t\t<TR>\n\t\t\t<TD ROWSPAN="1" PORT="sin1">sin1</TD>\n' +\
            '\t\t</TR>\n\t\t<TR>\n' +\
            '\t\t\t<TD ROWSPAN="1" PORT="sin2">sin2</TD>\n\t\t</TR>\n' +\
            '\t\t<TR>\n\t\t\t<TD ROWSPAN="1" PORT="sin3">sin3</TD>\n' +\
            '\t\t\t<TD ROWSPAN="4" PORT="sout1">sout1</TD>\n\t\t</TR>\n' +\
            '\t\t<TR>\n\t\t\t<TD ROWSPAN="1" PORT="sin4">sin4</TD>\n' +\
            '\t\t</TR>\n\t\t<TR>\n' +\
            '\t\t\t<TD ROWSPAN="1" PORT="sin5">sin5</TD>\n\t\t</TR>\n' +\
            '\t\t<TR>\n\t\t\t<TD ROWSPAN="1" PORT="sin6">sin6</TD>\n' +\
            '\t\t</TR>\n'
        actual_out = self._gen._get_html_rows_for_node(label, inputs, outputs)
        assert actual_out == expected_out
