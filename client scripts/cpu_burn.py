#!/usr/bin/env python

import datetime
import sys
import optparse
import logging
import os
import glob
import random
import sys
import copy

VERSION = '$Revision: 193 $'
SERVER = 'itb4.uchicago.edu'

def run_test():
  """
  Run test
  """

  logger = logging.getLogger('cpu_burn.py')
  logger.setLevel(logging.DEBUG)
  console_handler = logging.StreamHandler()
  console_handler.setLevel(logging.INFO)
  logger.addHandler(console_handler)
  logger.info("logging setup")

  invert()
  logger.info("finished inversion")
  logger.info("")
  sys.exit(0)



def mac(row1, row2, scaling_factor):
    """Multiply and Accumulate (MAC) row1 by scaling_factor and add row2"""
    temp = map(lambda x: x * scaling_factor, row1)
    for i in range(0, len(row1)):
        temp[i] = temp[i] + row2[i]
    return temp

def dot_product(row, column):
    """Get the dot product of a row and column"""
    sum = 0.0
    for i in range(0, len(row)):
        sum += row[i] * column[i]
    return sum

def column(matrix, j):
    """Get return a list with the jth column of the matrix"""
    temp = []
    for i in range(0, len(matrix)):
        temp.append(matrix[i][j])
    return temp

def invert(size = 600, seed =  42):
  """
  Generate and invert a matrix
  """

  random.seed(seed)

  # generate a size x 2 * size matrix with
  # a_ij is an integer between 1 and 100 if j < size
  # a_ij corresponds to the identity matrix if j > size
  # i.e. create a random size x size matrix augmented with the identity matrix
  if len(sys.argv) == 2:
      try:
          temp = int(sys.argv[1])
          size = temp
      except:
          pass
  matrix = []
  for i in range(0, size):
      matrix.append([])
      for j in range(0, 2*size):
          if j < size:
              matrix[i].append(random.randint(1, 100))
          elif (size + i) == j:
              matrix[i].append(1)
          else:
              matrix[i].append(0)

  # copy by value
  inverse = copy.deepcopy(matrix)
  # use gauss-jordan elimination to calculate inverse
  # fiddle around with row values to get an upper triangular matrix
  for i in range(0, size):
      # find pivot row and pivot
      pivot_row = i
      pivot_value = abs(inverse[i][i])
      for j in range(i, size):
          if abs(inverse[j][i]) > pivot_value:
              pivot_row = j
              pivot_value = abs(inverse[j][i])
      if pivot_row != i:
          temp = inverse[i]
          inverse[i] = inverse[j]
          inverse[j] = temp
      # convert pivot value to a floating point number if it isn't already
      pivot_value = float(pivot_value)

      # scale and add rows to reduce matrix to upper triangular form
      for j in range(i + 1, size):
         scaling_factor = inverse[j][i] /  pivot_value * -1
         inverse[j] = mac(inverse[i], inverse[j], scaling_factor)

  # fiddle around more with the rows to get a diagonal matrix
  # this time start from the bottom and work up
  foo = range(0, size)
  foo.reverse()
  for i in foo:
      value = float(inverse[i][i])
      for j in range(0, i):
          scaling_factor = inverse[j][i] / value * -1
          inverse[j] = mac(inverse[i], inverse[j], scaling_factor)

  # scale each row to get the identity matrix
  for i in range(0, size):
      scaling_factor =  1 / float(inverse[i][i])
      inverse[i] = map(lambda x: x * scaling_factor, inverse[i])

  # extract original and inverse matrices from augmented matrices
  # original = AI  inverse = IA^(-1)
  for i in range(0, size):
      matrix[i] = matrix[i][0:size]
      inverse[i] = inverse[i][size:2*size]

  # multiply original and inverse matrices  and verify that identity matrix results
  temp = copy.deepcopy(matrix)
  for i in range(0, size):
      for j in range(0, size):
          temp[i][j] = dot_product(matrix[i], column(inverse, j))



if __name__ == "__main__":
    run_test()
