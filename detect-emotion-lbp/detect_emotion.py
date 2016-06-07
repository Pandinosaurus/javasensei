#!/usr/bin/env python
# -*- coding: utf-8 -*

import cPickle
import glob
import os.path
import sys

import matplotlib.pyplot as plt
import numpy as np
from skimage.feature import local_binary_pattern
from sklearn import cross_validation
from sklearn.metrics import confusion_matrix
from sklearn.svm import LinearSVC

from util import *


class detect_emotion(object):
    classifier_face = cv2.CascadeClassifier(r"classifiers\lbpcascade_frontalface.xml")
    # classifier_eyes = cv2.CascadeClassifier(r"D:\OpenCV-Face-andmore-Tracker\Face(andmore)Tracker\Resources\haarcascades\eye.xml")
    classifier_eyes = cv2.CascadeClassifier(r"classifiers/eyes_lbp.xml")
    classifier_mouth = cv2.CascadeClassifier(
        r"D:\OpenCV-Face-andmore-Tracker\Face(andmore)Tracker\Resources\haarcascades\mouth.xml")
    classifier_nose = cv2.CascadeClassifier(
        r"D:\OpenCV-Face-andmore-Tracker\Face(andmore)Tracker\Resources\haarcascades\nose.xml")
    model = None
    X = None
    y = None
    emociones = ("enojado", "feliz", "neutral", "sorpresa", "triste")

    def __init__(self, modelPath=None, XPath = None, yPath = None):
        if not modelPath is None:
            self.model = cPickle.load(open(modelPath,"rb"))
        if not XPath is None:
            self.X = cPickle.load(open(XPath,"rb"))
        if not yPath is None:
            self.y = cPickle.load(open(yPath,"rb"))

    def predict(self, gray):
        returnValue = (False, "Rostro no encontrado")
        result, img = self.__get_image__(gray)
        if result:
            y = self.model.predict(img)
            returnValue = (True, self.emociones[y[0]])

        return returnValue
    
    def __get_image__(self, gray):
        roi_face = None
        roi_mouth = Roi()
        roi_nose = Roi()
        roi_eye_left = Roi()
        roi_eye_right = Roi()
        roi_eyebrown_left = Roi()
        roi_eyebrown_right = Roi()
        parts_founded = 0

        faces = self.classifier_face.detectMultiScale(gray)
        for (x, y, w, h) in faces[:1]:
            roi_face = gray[y:y + h, x:x + w]
            #Se cambia a un tamaño comun para que todos los facial patch tengan el mismo tamaño
            roi_face = cv2.resize(roi_face, (300,300))

            # Parte posible de la nariz, probando con 1/3 rostro
            h_roi_face = roi_face.shape[0]
            w_roi_face = roi_face.shape[1]
            first_part_face = int(h_roi_face * .3)

            candidate_nose = roi_face[first_part_face:h_roi_face - (first_part_face)]

            noses = self.classifier_nose.detectMultiScale(candidate_nose)
            for (xNose, yNose, wNose, hNose) in noses[:1]:

                roi_nose.x = xNose
                roi_nose.y = first_part_face + yNose
                roi_nose.w = wNose
                roi_nose.h = hNose
                roi_nose.image = candidate_nose[yNose:yNose + hNose, xNose:xNose + wNose]

                parts_founded += 1

                # A partir de donde termino la nariz, sacamos la parte restante para encontrar la boca
                candidate_mouth = roi_face[first_part_face + yNose + hNose:]
                mouths = self.classifier_mouth.detectMultiScale(candidate_mouth)
                for (xMouth, yMouth, wMouth, hMouth) in mouths[:1]:
                    roi_mouth.x = xMouth
                    roi_mouth.y = first_part_face + yNose + hNose + yMouth
                    roi_mouth.w = wMouth
                    roi_mouth.h = hMouth
                    roi_mouth.image = candidate_mouth[yMouth:yMouth + hMouth, xMouth:xMouth + wMouth]

                    parts_founded += 1

                # A partir de donde comienza la nariz, sacamos la parte restante para tratar de encontrar los ojos
                fix_forehead = int(h_roi_face * .15)
                halfFace = int(w_roi_face / 2)
                forehead = roi_face[fix_forehead:first_part_face + yNose]
                # Dividimos la imagen en 2 para tratar de encontrar ojoz izquierdo y ojo derecho
                candidate_eyeLeft = forehead[:, :halfFace]
                candidate_eyeRight = forehead[:, halfFace:]

                # Busqueda de ojo izquierdo
                eyeLeft = self.classifier_eyes.detectMultiScale(candidate_eyeLeft)
                if len(eyeLeft) > 0:
                    (xEyeLeft, yEyeLeft, wEyeLeft, hEyeLeft) = eyeLeft[0]
                    roi_eye_left.x = xEyeLeft
                    roi_eye_left.y = fix_forehead + yEyeLeft
                    roi_eye_left.w = wEyeLeft
                    roi_eye_left.h = hEyeLeft
                    roi_eye_left.image = candidate_eyeLeft[yEyeLeft:yEyeLeft + hEyeLeft, xEyeLeft:xEyeLeft + wEyeLeft]

                    # A partir del ojo se cubre un area esperando que la ceja se encuentre ahí, el filtrado hará el trabajo de descubrirla despues
                    roi_eyebrown_left.w = xEyeLeft + int(wEyeLeft * 1.6)
                    roi_eyebrown_left.h = fix_forehead + yEyeLeft
                    roi_eyebrown_left.x = int(xEyeLeft * .5)
                    roi_eyebrown_left.y = fix_forehead + int(yEyeLeft * .3)
                    roi_eyebrown_left.image = roi_face[fix_forehead + int(yEyeLeft * .3):fix_forehead + yEyeLeft,
                                              int(xEyeLeft * .5):xEyeLeft + int(wEyeLeft * 1.6)]
                    parts_founded += 1

                # Busqueda de ojo derecho
                eyeRight = self.classifier_eyes.detectMultiScale(candidate_eyeRight)
                if len(eyeRight) > 0:
                    (xEyeRight, yEyeRight, wEyeRight, hEyeRight) = eyeRight[0]
                    roi_eye_right.x = halfFace + xEyeRight
                    roi_eye_right.y = fix_forehead + yEyeRight
                    roi_eye_right.w = wEyeRight
                    roi_eye_right.h = hEyeRight
                    roi_eye_right.image = candidate_eyeRight[yEyeRight:yEyeRight + hEyeRight,
                                          xEyeRight:xEyeRight + wEyeRight]

                    roi_eyebrown_right.w = xEyeRight + int(wEyeRight * 1.6)
                    roi_eyebrown_right.h = fix_forehead + yEyeRight
                    roi_eyebrown_right.x = halfFace + int(xEyeRight * .5)
                    roi_eyebrown_right.y = fix_forehead + int(yEyeRight * .3)

                    roi_eyebrown_right.image = roi_face[fix_forehead + int(yEyeRight * .3): fix_forehead + yEyeRight,
                                               halfFace + int(xEyeRight * .5): halfFace + xEyeRight + int(wEyeRight * 1.6)]

                    parts_founded += 1

        not_result = (False,[])
        if parts_founded < 4:
            return not_result

        # Preprocesamiento y localización de puntos
        #boca
        roi_mouth.localizationPoints()
        # ojos
        roi_eye_left.localizationPointsCenter()
        roi_eye_right.localizationPointsCenter()
        # nariz
        roi_nose.localizationPointsCenter()
        # Filtrado en ceja derecha y posicion izquierda y derecha
        roi_eyebrown_right.localizationPoints()
        # Filtrado en ceja izquierda y posicion izquierda y derecha
        roi_eyebrown_left.localizationPoints()

        # obtenidos los puntos, aplicamos los facial patches
        width_patch = roi_face.shape[1] / 9
        half_patch = width_patch / 2
        puntos = {}

        # Estas areas son los puntos que ya se encontraron
        puntos["p1"] = Roi.createROI(roi_mouth.y + roi_mouth.pointLeft[0], roi_mouth.x + roi_mouth.pointLeft[1])
        puntos["p4"] = Roi.createROI(roi_mouth.y + roi_mouth.pointRight[0], roi_mouth.x + roi_mouth.pointRight[1])
        puntos["p18"] = Roi.createROI((roi_eyebrown_left.y + roi_eyebrown_left.pointRight[0]),
                                      roi_eyebrown_left.x + roi_eyebrown_left.pointRight[1])
        puntos["p19"] = Roi.createROI((roi_eyebrown_right.y + roi_eyebrown_right.pointLeft[0]),
                                      roi_eyebrown_right.x + roi_eyebrown_right.pointLeft[1])
        # p16 va en la parte central de los ojos
        puntos["p16"] = Roi.createROI(
            int(((roi_eye_left.y + roi_eye_left.pointRight[1]) + roi_eye_right.y + roi_eye_right.pointLeft[1]) / 2),
            int(((roi_eye_left.x + roi_eye_left.pointRight[0]) + roi_eye_right.x + roi_eye_right.pointLeft[0]) / 2))
        # p17 va justo arriba de p16
        puntos["p17"] = Roi.createROI(puntos["p16"].y - width_patch, puntos["p16"].x)
        # Estos puntos estan justo debajo de p1 y p4
        puntos["p9"] = Roi.createROI(puntos["p1"].y + width_patch, puntos["p1"].x)
        puntos["p11"] = Roi.createROI(puntos["p4"].y + width_patch, puntos["p4"].x)
        # Este punto va justo en medio de p9 y p11
        puntos["p10"] = Roi.createROI((puntos["p9"].y + puntos["p11"].y) / 2, (puntos["p9"].x + puntos["p11"].x) / 2)
        # Estos puntos van justo debajo del ojo (parte central)
        puntos["p14"] = Roi.createROI(roi_eye_right.y + roi_eye_right.h + int(roi_eye_right.h / 2),
                                      roi_eye_right.x + int(roi_eye_right.w / 2))
        puntos["p15"] = Roi.createROI(roi_eye_left.y + roi_eye_left.h + int(roi_eye_left.h / 2),
                                      roi_eye_left.x + int(roi_eye_left.w / 2))
        # Lado izquierdo de la nariz
        puntos["p2"] = Roi.createROI(roi_nose.y + roi_nose.pointLeft[1],
                                     roi_nose.x + roi_nose.pointLeft[0] - half_patch)
        puntos["p7"] = Roi.createROI(puntos["p2"].y, puntos["p2"].x - width_patch)  # justo a la izquierda de p2
        puntos["p8"] = Roi.createROI(puntos["p7"].y + width_patch, puntos["p7"].x)  # debajo de p7
        # Lado derecho de la nariz
        puntos["p5"] = Roi.createROI(roi_nose.y + roi_nose.pointRight[1],
                                     roi_nose.x + roi_nose.pointRight[0] + half_patch)
        puntos["p13"] = Roi.createROI(puntos["p5"].y, puntos["p5"].x + width_patch)  # justo a la derecha de p5
        puntos["p12"] = Roi.createROI(puntos["p13"].y + width_patch, puntos["p13"].x)  # debajo de p13
        # punto central entre nariz y ojo
        puntos["p3"] = Roi.createROI(
            int(((roi_eye_left.y + roi_eye_left.pointRight[1]) + (roi_nose.y + roi_nose.pointLeft[1])) / 2),
            int(((roi_eye_left.x + roi_eye_left.pointRight[0]) + (roi_nose.x + roi_nose.pointLeft[0])) / 2))  # Izquierdo
        puntos["p6"] = Roi.createROI(
            int(((roi_eye_right.y + roi_eye_right.pointLeft[1]) + (roi_nose.y + roi_nose.pointRight[1])) / 2),
            int(((roi_eye_right.x + roi_eye_right.pointLeft[0]) + (roi_nose.x + roi_nose.pointRight[0])) / 2))  # Derecho

        #Extraemos cada punto y lo agregamos al arreglo
        face_array = np.asarray([], dtype=roi_face.dtype)
        try:
            for clavePunto in puntos:
                punto = puntos[clavePunto]
                squareBegin = punto.getSquareBegin(half_patch)
                squareEnd = punto.getSquareEnd(half_patch)
                facial_patch = roi_face[squareBegin[1]:squareEnd[1], squareBegin[0]:squareEnd[0]]
                if not facial_patch.shape == (32,32):
                    return not_result
                #Se consigue el LBP
                lbp = local_binary_pattern(facial_patch, 8, 8, "uniform")
                hist, _ = np.histogram(lbp, bins=256, range=(0, 256),normed=True)
                face_array = np.concatenate((face_array, hist)) #Se concatenan los histogramas
        except:
            print "Unexpected error:", sys.exc_info()[0]
            raise
        return (True, face_array)

    def __load_images__(self, path=None, rostrosPath=None):
        if path is None:
            path = "D:/Respaldo Jose Luis/proyecto RVERK/RafD_Ordenado/"
        X, y = [], []
        rostros = []
        indice = -1
        for emocion in self.emociones:
            imagenes = glob.glob(path + emocion + "\\*.jpg")
            indice += 1
            try:
                for imagen in imagenes:
                    frame = cv2.imread(imagen)
                    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
                    result, array = self.__get_image__(gray)
                    if result:
                        X.append(array)
                        y.append(indice)
                        rostros.append({"emocion":emocion, "imagen":frame})
            except IOError, (errno, strerror):
                print "I/O error({0}): {1}".format(errno, strerror)
            except:
                print "Unexpected error:", sys.exc_info()[0]
                raise
        if not rostrosPath is None:
            cPickle.dump(rostros, open(rostrosPath,"wb"), cPickle.HIGHEST_PROTOCOL)
        return [X, y]

    @staticmethod
    def create_model_training(savePath, XPath = None, yPath=None, path=None, rostrosPath=None):
        detector = detect_emotion()
        X, y = detector.__load_images__(path, rostrosPath)
        #X = cPickle.load(open("data/X.x","rb"))
        #y = cPickle.load(open("data/y.y","rb"))
        detector.X = X
        detector.y = y
        svm = LinearSVC()
        svm.fit(X,y)
        detector.model = svm
        cPickle.dump(svm, open(savePath, "wb"))
        pathSVM = os.path.dirname(os.path.abspath(savePath))
        if XPath is None:
            XPath = os.path.join(pathSVM, "X.x")
        if yPath is None:
            yPath = os.path.join(pathSVM, "y.y")
        cPickle.dump(X, open(XPath, "wb"))
        cPickle.dump(y, open(yPath,"wb"))
        return detector

    def crossValidation(self, cv=10, graficar=False):
        scores = cross_validation.cross_val_score(self.model,self.X,self.y)
        print("Precisión: %0.2f (+/- %0.2f)" % (scores.mean(), scores.std() * 2))
        #Matriz de confusión
        yTrue = map(lambda index: self.emociones[index], self.y)
        yPred = self.model.predict(self.X)
        yPred = map(lambda index: self.emociones[index], yPred)
        cm = confusion_matrix(yTrue, yPred, self.emociones)
        self.cm = cm
        print(cm)

        if graficar:
            norm_conf = []
            for i in cm:
                a = 0
                tmp_arr = []
                a = sum(i, 0)
                for j in i:
                    tmp_arr.append(float(j) / float(a))
                norm_conf.append(tmp_arr)

            fig = plt.figure()
            plt.clf()
            ax = fig.add_subplot(111)
            ax.set_aspect(1)
            res = ax.imshow(np.array(norm_conf), cmap=plt.cm.jet,
                            interpolation='nearest')

            width, height = cm.shape

            for x in xrange(width):
                for y in xrange(height):
                    ax.annotate(str(cm[x][y]), xy=(y, x),
                                horizontalalignment='center',
                                verticalalignment='center')

            cb = fig.colorbar(res)
            plt.xticks(range(width), self.emociones)
            plt.yticks(range(height), self.emociones)

#detector = detect_emotion.create_model_training("data\modelo.m")
#detector = detect_emotion("data/modelo.m","data/X.x","data/y.y")
#detector.crossValidation()