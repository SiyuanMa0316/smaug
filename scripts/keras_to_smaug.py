#!/usr/bin/env python
#
# Export the parameters of a trained model to the SMAUG txt data format.
#
# This script only exports the weights for the layer types supported by SMAUG.
# In addition, it omits biases for standard convolutional layers, as SMAUG
# doesn't handle them.
#
# In addition to weights, this script also exports one training input and its
# corresponding label.
#
# Note: this script does not take into account any transformations that need to
# be done for data layout! The user must handle data layout him/herself.
#
# Usage:
#
#   import keras_to_smaug
#   # Build your keras model.
#   convert_to_smaug.save_model(
#      model, x_train, y_train, model_name, data_alignment)

import os
import numpy as np

from keras.applications import mobilenet
from keras.layers import Dense, Conv2D, AveragePooling2D, MaxPooling2D, BatchNormalization
from keras.models import Sequential

def calc_padding(value, padding):
  if padding == 0 or value % padding == 0:
    return 0
  return padding - (value % padding)

def get_num_layers(model_layers):
  counted_layer_types = [Dense,
                         Conv2D,
                         AveragePooling2D,
                         MaxPooling2D,
                         BatchNormalization,
                         mobilenet.DepthwiseConv2D]
  num = 0
  for layer in model_layers:
    if isinstance(layer, mobilenet.DepthwiseConv2D):
      print("[WARNING]: Depthwise convolutional layers are not well handled "
            "yet, since we don't support biases on the depthwise layers but we "
            "do for the pointwise layers.")
    for t in counted_layer_types:
      if isinstance(layer, t):
        num += 1
        break

  return num

def get_padded_size(shape, data_alignment):
  """ Get the total size of shape, accounting for data alignment. """
  shape = list(shape)
  inner_dim = shape[-1]
  inner_dim += calc_padding(inner_dim, data_alignment)
  shape[-1] = inner_dim
  return np.prod(shape)

def get_num_parameters(model_layers, data_alignment):
  num = 0
  for layer in model_layers:
    for w in layer.get_weights():
      # Skip conv biases.
      if isinstance(layer, Conv2D):
        if len(w.shape) == 1:
          continue
      num += get_padded_size(w.shape, data_alignment)
  return num

def print_padded_array(outfile, data, data_alignment, fmt="%5.5f"):
  """ Print the data to a file, adding zero padding if necessary.

  The data is dumped linearly -- the shape of the data is not preserved.  A
  terminating comma is added at the end, but no newline.

  Args:
    outfile: The output file.
    data: An np.array containing the data to be dump.
    data_alignment: The required data alignment at the innermost dimension of
      the data.
    fmt: The format string for each element (e.g. "%d, %4.0f").
  """
  data_shape = list(data.shape)
  data_shape = [1] * (4 - len(data_shape)) + data_shape
  data = np.reshape(np.array(data), data_shape)

  for i in range(data_shape[0]):
    for j in range(data_shape[1]):
      for k in range(data_shape[2]):
        arr2str = ",".join([fmt % e for e in data[i, j, k, :]])
        # Add padding.
        pad = calc_padding(data_shape[3], data_alignment)
        arr2str += ",0" * pad
        arr2str += ","
        outfile.write(arr2str)

def print_txt_global_section(outfile, arch, num_layers, data_alignment):
  outfile.write("===GLOBAL BEGIN===\n")
  outfile.write("# ARCHITECTURE = %s\n" % arch)
  # SMAUG counts the input layer as a layer.
  outfile.write("# NUM_LAYERS = %d\n" % (num_layers + 1))
  outfile.write("# DATA_ALIGNMENT = %d\n" % data_alignment)
  outfile.write("===GLOBAL END===\n")

def print_txt_weights_section(outfile, layers, data_alignment,
                              transpose_weights):
  outfile.write("===WEIGHTS BEGIN===\n")
  outfile.write("# NUM_ELEMS %d\n" % get_num_parameters(layers, data_alignment))
  outfile.write("# TYPE float\n")

  for i, layer in enumerate(layers):
    for w in layer.get_weights():
      if isinstance(layer, Conv2D) and len(w.shape) == 1:
        continue
      if transpose_weights and isinstance(layer, Dense):
        w = w.T
      print_padded_array(outfile, w, data_alignment)

  outfile.write("\n===WEIGHTS END===\n")

def print_txt_inputs_section(outfile, x_train, data_alignment):
  outfile.write("===DATA BEGIN===\n")
  outfile.write("# NUM_ELEMS %d\n" % get_padded_size(
      x_train[0, :].shape, data_alignment))
  outfile.write("# TYPE float\n")
  print_padded_array(outfile, x_train[0, :], data_alignment)
  outfile.write("\n===DATA END===\n")

def print_txt_labels_section(outfile, y_train):
  outfile.write("===LABELS BEGIN===\n")
  outfile.write("# NUM_ELEMS 1\n")
  outfile.write("# TYPE int\n")
  print_padded_array(outfile, np.argmax(y_train[0, :]), 0, fmt="%d")
  outfile.write("\n===LABELS END===\n")

def print_txt_model(model, x_train, y_train, model_name,
                    arch, data_alignment, transpose_weights):
  filename = "%s.txt" % model_name
  with open(filename, "w") as f:
    print_txt_global_section(
        f, arch, get_num_layers(model.layers), data_alignment)
    print_txt_weights_section(
        f, model.layers, data_alignment, transpose_weights)
    print_txt_inputs_section(f, x_train, data_alignment)
    print_txt_labels_section(f, y_train)

  print "Model parameters saved to %s." % filename

def save_model(model, x_train, y_train, model_name, arch,
               data_alignment=0, transpose_weights=False):
  """ Save the Keras model in SMAUG txt format.

  Arguments:
    model: A keras.models.Sequential model.
    x_train: The complete set of training examples. The first dimension is
      assumed to be over the number of inputs.
    y_train: The complete set of training targets.
    model_name: A string name for this model. The output file will be named
      "model_name.txt".
    arch: The name of the architecture (backend) that will use this model (e.g.
      SMIV).
    data_alignment: Required data alignment at the innermost dimension.
    transpose_weights: If true, save the weights in colmajor order; otherwise,
      save in rowmajor.
  """
  assert(isinstance(model, Sequential))
  assert(isinstance(model_name, str))
  assert(isinstance(arch, str))
  assert(isinstance(data_alignment, int))
  assert(isinstance(transpose_weights, bool))
  print_txt_model(model, x_train, y_train, model_name + arch.lower(),
                  arch, data_alignment, transpose_weights)
