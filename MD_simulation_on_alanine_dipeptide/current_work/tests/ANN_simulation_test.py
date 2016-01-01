'''This is a test for functionality of ANN_simulation.py
'''

import sys

sys.path.append('../src/')  # add the source file folder

from ANN_simulation import *
from nose.tools import assert_equal, assert_almost_equal


class test_coordinates_file(object):
    @staticmethod
    def test_coor_data():
        filename = 'dependency/biased_output_fc_1000_x1_0.7_x2_-1.07_coordinates.txt'
        my_file = single_simulation_coordinates_file(filename)
        expected = np.array([1.875  , 2.791  , -0.215 , 3.338  , 2.897 ,  0.193   ,
            4.032  , 3.862 ,  -0.414 , 5.350  , 4.301  , 0.000   ,
            5.314 ,  5.734  , 0.511  , 5.119  , 6.718  , -0.370  ,
            4.974  , 8.120  , -0.034  ])
        for item in range(21):
            assert_almost_equal(my_file._coor_data[0][item], expected[item])

        assert_equal(my_file._coor_data.shape[0], 100)
        return

class test_simulation_utils(object):
    def test_get_many_cossin_from_coordiantes_in_list_of_files(self):
        list_of_files = ['dependency/biased_output_fc_1000_x1_0.7_x2_-1.07_coordinates.txt']
        actual = sutils.get_many_cossin_from_coordiantes_in_list_of_files(list_of_files)
        assert_equal(100, len(actual))
        assert_equal(8, len(actual[0]))
        expected = [-0.97750379745637539, -0.40651951247361273, 0.32798972133405019, -0.99736251135112719,
                    0.21091781802011281, -0.91364209949969788, -0.94468129160008874, 0.07258113357734837]

        assert_almost_equal(expected, actual[0])
        return

class test_ANN_simulation(object):
    pass
