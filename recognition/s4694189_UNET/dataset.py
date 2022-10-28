# -*- coding: utf-8 -*-
"""dataset.ipynb

Automatically generated by Colaboratory.

Original file is located at
    https://colab.research.google.com/drive/1mnY3QzBRkE8Vtazx37l0yevqP0JF_rhj
"""

from keras.utils import normalize
import os
import glob
import cv2
import numpy as np
import matplotlib.pyplot as plt

import zipfile
with zipfile.ZipFile("/content/drive/MyDrive/dataset/ISIC-2017_Training_Data.zip","r") as zip_ref:
    zip_ref.extractall("train_images")

import zipfile
with zipfile.ZipFile("/content/drive/MyDrive/dataset/ISIC-2017_Training_Part1_GroundTruth.zip","r") as zip_ref:
    zip_ref.extractall("mask_train")

images_list = []
for image_path in glob.glob("train_images/ISIC-2017_Training_Data/"):
  print(image_path)

transformed_X = 256
transformed_Y = 256
def load_images(path):
  image_list = []
  for fi in os.listdir(path):
    #print(fi)
    if fi.endswith(".csv") or "superpixels" in fi:
      continue
    img = cv2.imread(os.path.join(path, fi),cv2.IMREAD_COLOR)
    img = cv2.resize(img,(transformed_Y,transformed_X))
    img = img / 255.0
    img = img.astype(np.float32)
    image_list.append(img)
  image_list = np.array(image_list)
  return image_list

def load_masks(path):
  masks_list = []
  for fi in os.listdir(path):
    #print(fi)
    if fi.endswith(".csv") or "superpixels" in fi:
      continue
    mask = cv2.imread(os.path.join(path, fi),cv2.IMREAD_GRAYSCALE)
    mask = cv2.resize(mask,(transformed_Y,transformed_X))
    mask = mask / 255.0
    mask = mask.astype(np.float32)
    masks_list.append(mask)
  masks_list = np.array(masks_list)
  return masks_list

X_train = load_images("/content/train_images/ISIC-2017_Training_Data")

print(X_train)

masks_images = load_masks("/content/mask_train/ISIC-2017_Training_Part1_GroundTruth")

print(masks_images.shape)

from sklearn.preprocessing import LabelEncoder
labelencoder = LabelEncoder()
n,height,width = masks_images.shape
reshape_masks = masks_images.reshape(-1,1)
masks_after_encoding = labelencoder.fit_transform(reshape_masks)
encoded_masks_with_original_size = masks_after_encoding.reshape(n,height,width)
np.unique(encoded_masks_with_original_size)

img = load_images("train_images/ISIC-2017_Training_Data/")
def imshow(title, image = None, size = 6):
    if image.any():
      w, h = image.shape[0], image.shape[1]
      aspect_ratio = w/h
      plt.figure(figsize=(size * aspect_ratio,size))
      plt.imshow(cv2.cvtColor(image, cv2.COLOR_BGR2RGB))
      plt.title(title)
      plt.show()
    else:
      print("Image not found")

load_images("/content/train_images/")

# import tensorflow as tf
# import tf.keras
import os
import numpy as np
from PIL import Image
# import torch

training_images = "/content/drive/MyDrive/dataset/ISIC-2017_Training_Data.zip"
masks_train_image = "/content/drive/MyDrive/dataset/ISIC-2017_Training_Part1_GroundTruth.zip"

validation_images = "/content/drive/MyDrive/dataset/ISIC-2017_Validation_Data.zip"
masks_validate_image = "/content/drive/MyDrive/dataset/ISIC-2017_Validation_Part1_GroundTruth.zip"

test_images = "/content/drive/MyDrive/dataset/ISIC-2017_Test_v2_Data.zip"
masks_validate_image = "/content/drive/MyDrive/dataset/ISIC-2017_Test_v2_Part1_GroundTruth.zip"

"""
    # Function to load the preprocessed images
    # This function only loads images into X type of variables 
    # i.e. the real time images  
"""


def load_x_images(path):
    X = []
    for fi in os.listdir(path):
        if fi.endswith(".csv") or "superpixels" in fi:
            continue
        x = Image.open(os.path.join(path, fi)).resize((256, 256))
        x = np.array(x)
        # print(x.shape)
        # exit(0);
        x = x / 255.0
        # print(x_train.shape)
        X.append(x)

    np.stack(X)

    """
        # All the list are now converted to numpy array
        # List are converted to numpy array because converting variables 
        # into tensor is made faster and program runs faster 
        # else the running and compiling is slowed down
    """

    X = np.array(X)
    # X = torch.tensor(X)

    return X


"""
    # Function to load the preprocessed images
    # This function only loads images into Y type of variables 
    # i.e. the images with detection of cancer
    # Non real time images 
"""


def load_y_images(path):
    Y = []
    for fi in os.listdir(path):
        if fi.endswith(".csv") or "superpixels" in fi:
            continue
        y = Image.open(os.path.join(path, fi)).resize((256, 256), Image.Resampling.NEAREST)
        y = np.array(y)

        # print(x_train.shape)
        Y.append(y)

    Y = np.array(Y)
    Y = Y / 255
    # Y = torch.tensor(Y)
    Y = Y[..., None]
    return Y


"""
    # Loading normal images for training the model
    # i.e. X_train is loaded with images 
"""

print("Program starting")

X_train = load_x_images(X_train_path)

# for f in os.listdir(X_train_path):
#     if f.endswith(".csv") or "superpixels" in f:
#         continue
#     x_train = Image.open(os.path.join(X_train_path, f)).resize((256, 256))
#     x_train = np.array(x_train)
#     x_train = x_train / 255.0
#     # print(x_train.shape)
#     X_train.append(x_train)
#
# np.stack(X_train)
print("********* Data loading for X_training complete *********")

"""
    # Loading segmented images for training the model
    # i.e. Y_train is loaded with segmented images with cancer detected
"""
Y_train = load_y_images(Y_train_path)
# for f in os.listdir(Y_train_path):
#     if f.endswith(".csv") or "superpixels" in f:
#         continue
#     y_train = Image.open(os.path.join(Y_train_path, f)).resize((256, 256))
#     y_train = np.array(y_train)
#     # print(y_train.shape)
#     Y_train.append(y_train)
#
# np.stack(Y_train)

# print(Y_train)
# print(np.unique(Y_train))
# print(Y_train.shape)
#
# exit(0)
print("********* Data loading for Y_training complete *********")

"""
    # Loading normal images for validating the model
    # i.e. X_validate is loaded with images
"""

X_validate = load_x_images(X_validate_path)
print("********* Data loading for X_validating complete *********")

"""
    # Loading segmented images for the validation of model
    # i.e. Y_validate is loaded with segmented images
"""

Y_validate = load_y_images(Y_validate_path)
print("********* Data loading for Y_validating complete *********")

"""
    # Loading normal images for testing the model
    # i.e. X_test is loaded with images
"""

X_test = load_x_images(X_test_path)
print("********* Data loading for X_testing complete *********")

"""
    # Loading segmented images for testing the model
    # i.e. Y_test is loaded with images
"""

Y_test = load_y_images(Y_test_path)
print("********* Data loading for Y_testing complete *********")

"""
    # Shapes have been printed 
    # to check the number of images and sizes of the variables
    # Hence checking the loading of dataset is done correctly  
"""

print(X_train.shape)
# print(X_train)
# print(Y_train.shape)

print(X_validate.shape)
# print(X_validate)

print(X_test.shape)
# print(X_test)

