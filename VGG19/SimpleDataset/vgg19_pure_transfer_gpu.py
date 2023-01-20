# -*- coding: utf-8 -*-
"""Vgg16_Pure_Transfer.ipynb

Automatically generated by Colaboratory.

Original file is located at
    https://colab.research.google.com/drive/1ieTbo4IXfBq07cvE99nYjTcFKs0Px350
"""

import tensorflow as tf
from tensorflow.keras.models import Model, model_from_yaml
from tensorflow.keras.models import Sequential
from tensorflow.keras.layers import Activation, Dropout, Flatten, Dense,AveragePooling2D
from tensorflow.keras.applications import VGG19
from tensorflow.keras.applications.vgg19 import preprocess_input
from tensorflow.keras.optimizers import SGD,Adam
from tensorflow.keras.preprocessing.image import ImageDataGenerator
from tensorflow.keras.callbacks import ModelCheckpoint,EarlyStopping,CSVLogger, LearningRateScheduler,ReduceLROnPlateau

import numpy as np
import time
import matplotlib.pyplot as plt
import keras
import sys

"""# Transfert Pure

Save and load models
"""

def saveModel(model, savename):
  # serialize model to YAML
  model_yaml = model.to_yaml()
  with open(savename+".yaml", "w") as yaml_file:
    yaml_file.write(model_yaml)
    print("Yaml Model ",savename,".yaml saved to disk")
  # serialize weights to HDF5
  model.save_weights(savename+".h5")
  print("Weights ",savename,".h5 saved to disk")


def loadModel(savename):
  with open(savename+".yaml", "r") as yaml_file:
    model = model_from_yaml(yaml_file.read())
  print("Yaml Model ",savename,".yaml loaded ")
  model.load_weights(savename+".h5")
  print("Weights ",savename,".h5 loaded ")
  return model

"""Load --> generate --> itterate"""

nClasses=2
train_image_dir="../../Data/SimpleDatabase/SimpleData/Train/"

img_width = 224  # Archi du reseau
img_height = 224
channels = 3
batch_size = 8
epochs =100

train_datagen=ImageDataGenerator(
        rotation_range=15,
        width_shift_range=0.1,
        height_shift_range=0.1,
        shear_range=0.1,
        rescale=1. / 255,
        zoom_range=0.1,
        horizontal_flip=True,
        fill_mode = 'nearest',
        #preprocessing_function = preprocess_input,
        validation_split=0.20)


train_generator=train_datagen.flow_from_directory(
        train_image_dir,
        target_size=(img_width,img_height),
        batch_size=batch_size,shuffle=False,
        class_mode='categorical',
        subset='training')

validation_generator=train_datagen.flow_from_directory(
        train_image_dir,
        target_size=(img_width,img_height),
        batch_size=batch_size,
        class_mode='categorical',shuffle=False,
        subset='validation')


#################################### GPU #######################################
gpus = tf.config.experimental.list_physical_devices('GPU')
if gpus:
  try:
    # Currently, memory growth needs to be the same across GPUs
    for gpu in gpus:
      tf.config.experimental.set_memory_growth(gpu, True)
    logical_gpus = tf.config.experimental.list_logical_devices('GPU')
    print(len(gpus), "Physical GPUs,", len(logical_gpus), "Logical GPUs")
  except RuntimeError as e:
    # Memory growth must be set before GPUs have been initialized
    print(e)

################################################################################

modelBase=VGG19(include_top=False, weights='imagenet',input_shape=(img_width,img_height,channels))
# include_top=False --> on ne charge pas les 3 dérnières couches FC de VGG19 (Voir archi pour comprendre)

model = modelBase.output
model = tf.keras.layers.Conv2D(filters=64,kernel_size=(3,3),padding="same", activation='relu' )(model)
model = AveragePooling2D(pool_size =(3, 3),padding="same")(model)
model = Flatten(name ='Flatten')(model)
model = Dense(128, activation = 'relu')(model)
model = Dropout(0.5)(model)
model = Dense(64, activation = 'relu')(model)
model = Dropout(0.5)(model)
model = Dense(2, activation = 'softmax')(model)

model = Model(inputs = modelBase.input, outputs = model)

for i in range(len(modelBase.layers)):
    model.layers[i].trainable = False

#################################################################################################################
#sgd = SGD(lr=0.001, decay=1e-6, momentum=0.9, nesterov=True)
#################################################################################################################
adam = Adam(learning_rate=0.001,decay=1e-5)

loss = tf.keras.losses.BinaryCrossentropy(from_logits=False, label_smoothing=0,name='binary_crossentropy')
model.compile(loss=loss, optimizer=adam, metrics=['binary_accuracy'])
print(model.summary())
early_stop = EarlyStopping(monitor='val_loss', min_delta=0.0001, patience=10, verbose=2)
lr_reducer = ReduceLROnPlateau(factor=0.5, cooldown=0, patience=5, min_lr=0.5e-6)
csv_logger = CSVLogger('Transfert_VGG19.csv')

STEP_SIZE_TRAIN=train_generator.n//train_generator.batch_size
STEP_SIZE_VALID=validation_generator.n//validation_generator.batch_size
if STEP_SIZE_VALID == 0:
    sys.exit(1)

start_time = time.time()
print("debut execution "+str(start_time))

history=model.fit(x=train_generator,
                steps_per_epoch=STEP_SIZE_TRAIN,
                epochs=epochs,
                validation_data=validation_generator,
                validation_steps=STEP_SIZE_VALID,
                shuffle=True,verbose=1,
                callbacks=[lr_reducer, early_stop, csv_logger])

saveModel(model,'Transfert_VGG19')
