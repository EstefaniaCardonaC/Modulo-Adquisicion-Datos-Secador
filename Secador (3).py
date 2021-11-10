# Import necessary modules
import sys
import os
import requests
import webbrowser
from os import path
from os import remove
import subprocess
import shutil
from PyQt5.QtWidgets import  QDialog,QApplication,QMessageBox, QMainWindow,QComboBox, QRadioButton, QGridLayout ,QWidget, QFrame, QLCDNumber,QPushButton, QLabel, QLineEdit, QGroupBox, QTabWidget, QVBoxLayout, QHBoxLayout
from PyQt5.QtGui import QIcon , QFont, QPixmap,QDoubleValidator
from PyQt5 import QtCore, QtGui
from PyQt5.QtCore import Qt, QThread, pyqtSignal, QMetaObject,QFile,QIODevice,QTextStream
from PyQt5.QtCore import QMetaObject as QMO
import threading
import MAX6675 as MAX6675
import HX711 as HX711
import time
import RPi.GPIO as GPIO
import sip
import numpy as np
from pyqtgraph import PlotWidget, plot
import pyqtgraph as pg
import pyqtgraph.exporters
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.base import MIMEBase
from email import encoders
from datetime import datetime
from validate_email import validate_email

#PINES SENSOR TEMPERATURA 1
CSK=4
CS=3
DO=2
units="c"

#PINES SENSOR TEMPERATURA 2
CSK2=11
CS2=9
DO2=10

#PINES SENSOR TEMPERATURA 3
CSK3=26
CS3=19
DO3=13

dout_pin=23
pd_sck_pin=24
GPIO.setmode(GPIO.BCM)
GPIO.setwarnings (False)


class Temperatura(QtCore.QThread):
    valorCambiado=pyqtSignal(float,float,float)
    
    def run(self):
        while True:
        
            sensor = MAX6675.MAX6675(CSK, CS, DO, units)
            sensor2 = MAX6675.MAX6675(CSK2, CS2, DO2, units)
            sensor3 = MAX6675.MAX6675(CSK3, CS3, DO3, units)
            
            
            temp1 = float(sensor.get_temp())
            temp2 = float(sensor2.get_temp())
            temp3 = float(sensor3.get_temp())
            
            time.sleep(1)
            
            if str(temp1)!="nan" and str(temp2) !="nan" and str(temp3)!="nan":
                self.valorCambiado.emit(temp1,temp2,temp3)

class CeldaCarga(QtCore.QThread):
    nuevoValor=pyqtSignal(float)
    
    hx = HX711.HX711(dout_pin, pd_sck_pin)
    err = hx.zero()
    hx.set_scale_ratio(1041.3466522678186)
    #hx.set_scale_ratio(429.2428)
    def run(self):
        while True:
            masa=float(self.hx.get_weight_mean(10))
            self.nuevoValor.emit(masa)
            time.sleep(1)
            
class Temporizador(QtCore.QThread):

    tiempoMasa=pyqtSignal(float,float)
    valorMasa=pyqtSignal(float)
    valorTiempo=pyqtSignal(str)
    
    
    def run(self):
        isRunning=True
        valorInicialMasa=float(CeldaCarga.hx.get_weight_mean(2))
        contador=0
        indicadorDatos=0
        datos=[]
        while isRunning:
            contador=contador+1
            if contador<60:
                seg=int(contador)
                minu=0
                hora=0
            else:
                seg=int(contador%60)
                minu=int(contador//60)
            if minu<60:
                pass
            elif minu>=60:
                hora=int(minu//60)
                minu=int(minu%60)
            if int(seg)<10 and int(minu)<10 and int(hora)<10:
                tiempo="0"+str(hora)+":"+"0"+str(minu)+":"+"0"+str(seg)
                self.valorTiempo.emit(tiempo)
                
            elif int(seg)>=10 and int (minu)<10 and int(hora)<10:
                tiempo="0"+str(hora)+":"+"0"+str(minu)+":"+str(seg)
                self.valorTiempo.emit(tiempo)
                
            elif int (seg)>=10 and int(minu)>=10 and int(hora)<10:
                tiempo="0"+str(hora)+":"+str(minu)+":"+str(seg)
                self.valorTiempo.emit(tiempo)

                
            elif int(seg)>=10 and int(minu)>=10 and int(hora)>=10:
                tiempo=str(hora)+":"+str(minu)+":"+str(seg)
                self.valorTiempo.emit(tiempo)
                
            elif int(seg)<10 and int(minu)>=10 and int(hora)<10:
                tiempo="0"+str(hora)+":"+str(minu)+":"+"0"+str(seg)
                self.valorTiempo.emit(tiempo)
                
            elif int(seg)<10 and int(minu)>=10 and int(hora)>=10:
                tiempo=str(hora)+":"+str(minu)+":"+"0"+str(seg)
                self.valorTiempo.emit(tiempo)

            elif int(seg)<10 and int(minu)<10 and int(hora)>=10:
                tiempo=str(hora)+":"+"0"+str(minu)+":"+"0"+str(seg)
                self.valorTiempo.emit(tiempo)
            masa=float(CeldaCarga.hx.get_weight_mean(1))
            
            resta=valorInicialMasa-masa
            if (resta<0):
                resta=-resta
            if (resta)<10:
                datos.append(masa)
                if contador==1:
                    self.tiempoMasa.emit(contador,masa)
                if contador%60==0:
                    suma=0
                    for a in datos:
                        suma=a+suma
                    
                    masaPromedio=suma/len(datos)
                    self.tiempoMasa.emit(contador,masaPromedio)
                    self.valorMasa.emit(masa)
                    datos=[]
                    
                valorInicialMasa=masa
                
                
            time.sleep(1)

    
class Interfaz(QWidget):

    def __init__(self):
        super().__init__()
        self.setWindowTitle('Secador convectivo UdeA') 
        tabWidget=QTabWidget()
        tabWidget.setStyleSheet("QTabBar::tab { height: 70px; width: 300px;}")
        tabWidget.addTab(Principal(), "Principal")
        tabWidget.addTab(Graficas_VS(), "Gráficas Velocidad Secado")
        tabWidget.addTab(Graficas_H(), "Gráficas Humedad")
        tabWidget.addTab(transmitirDatos(), "Transmisión remota")
        tabWidget.addTab(apagar(),"Apagar") 

        vbox= QVBoxLayout()
        vbox.addWidget(tabWidget)

        self.setLayout(vbox)
        self.setFixedSize(800,410)
        tabWidget.setStyleSheet("QTabWidget::pane {margin: 0px,1px,1px,1px; border: 2px solid #020202;border-radius: 7px;padding: 1px;background-color: #E6E6E3;}")
        self.show()

        inicio=pantallaInicio()
        inicio.exec()
        
class Principal (QWidget):
    
    def __init__(self):
        super().__init__()
  
        hbox=QHBoxLayout()
        grupoGrafica=QGroupBox("Operación de secado")
        grupoGrafica.setStyleSheet("background-color: #626567;" "color: #F7F9F9")
        grupoGrafica.setFont(QFont("Sanserif",10))
        grupoGrafica.setFixedSize(355,330)
        grupoCalculos=QGroupBox()
        grupoCalculos.setStyleSheet("background-color: #626567;" "color: #F7F9F9" )
        grupoCalculos.setFont(QFont("Sanserif",10))
    
        #SECCION GRAFICA PRINCIPAL Y OPERACIONES
        vboxgraficas=QVBoxLayout()

        #Sección Gráfica masa vs tiempo
        seccion_masa_vs_tiempo=QHBoxLayout()
        vboxgraficas.addLayout(seccion_masa_vs_tiempo)
        grupo_grafica=QGroupBox("Masa vs Tiempo")
        grupo_grafica.setStyleSheet("color: #34495E;" "background-color: #F7F9F9;"
                                 "border-style=dashed;"
                                 "border-width=3px;"
                                 "border-color=#229954")
        self.graphWidget = pg.PlotWidget()
        self.plot=self.graphWidget.plot()
        self.graphWidget.setLabel(axis='left', text='Masa (g)')
        self.graphWidget.setLabel(axis='bottom', text='Tiempo (s)')
        self.graphWidget.setTitle("Masa vs Tiempo")
        vboxgrafica=QVBoxLayout()
        vboxgrafica.addWidget(self.graphWidget)
        grupo_grafica.setLayout(vboxgrafica)
        seccion_masa_vs_tiempo.addWidget(grupo_grafica)


        #Sección variables inicio/reseteo
        
        #SECCION VARIABLES
        vboxoperaciones=QVBoxLayout()

        #Sección masa y tiempo de operación

        seccion_masa_tiempo=QHBoxLayout()
        vboxoperaciones.addLayout(seccion_masa_tiempo)
        grupo_masa=QGroupBox("Masa")
        grupo_masa.setStyleSheet("color: #34495E;" "background-color: #F7F9F9;"
                                 "border-style=dashed;"
                                 "border-width=3px;"
                                 "border-color=#229954")
        grupo_tiempo=QGroupBox("Tiempo de operación")
        grupo_tiempo.setStyleSheet("color: #34495E;" "background-color: #F7F9F9;")
        seccion_masa_tiempo.addWidget(grupo_masa)
        seccion_masa_tiempo.addWidget(grupo_tiempo)        

        vboxMasa=QVBoxLayout()
        self.masaCelda=QLabel('{:0.1f}'.format(0))
        self.masaCelda.setFont(QFont("Sanserif",20))
        vboxMasa.addWidget(self.masaCelda)
        BotonCero=QPushButton("CALIBRAR\nCELDA")
        BotonCero.clicked.connect(self.calibrar)
        BotonCero.setIcon(QIcon('/home/pi/MAX6675/iconos/zero.png'))
        BotonCero.setIconSize((QtCore.QSize(30,30)))
        BotonCero.setStyleSheet("color: #213142;" "font-family: Segoe UI;" "font-weight: bold")
        vboxMasa.addWidget(BotonCero)
        grupo_masa.setLayout(vboxMasa)

        hboxTiempo=QHBoxLayout()
        self.cronometro=QLabel('{}'.format("00:00:00"))
        self.cronometro.setFont(QFont("Sanserif",20))
        hboxTiempo.addWidget(self.cronometro)
        grupo_tiempo.setLayout(hboxTiempo)

        #Sección temperaturas
        seccion_temperaturas=QHBoxLayout()
        vboxoperaciones.addLayout(seccion_temperaturas)
        grupo_temperatura_cabina=QGroupBox("Cabina")
        grupo_temperatura_cabina.setStyleSheet("color: #34495E;" "background-color: #F7F9F9;"
                                 "border-style=dashed;"
                                 "border-width=3px;"
                                 "border-color=#229954")
        grupo_temperatura_ducto1=QGroupBox("Ducto 1")
        grupo_temperatura_ducto1.setStyleSheet("color: #34495E;" "background-color: #F7F9F9;"
                                 "border-style=dashed;"
                                 "border-width=3px;"
                                 "border-color=#229954")
        grupo_temperatura_ducto2=QGroupBox("Ducto 2")
        grupo_temperatura_ducto2.setStyleSheet("color: #34495E;" "background-color: #F7F9F9;"
                                 "border-style=dashed;"
                                 "border-width=3px;"
                                 "border-color=#229954")
        
        hboxTemperaturaCabina=QHBoxLayout()
        self.temperaturaCabina=QLabel('{:0.1f}'.format(0))
        self.temperaturaCabina.setFont(QFont("Sanserif",18))
        hboxTemperaturaCabina.addWidget(self.temperaturaCabina)
        grupo_temperatura_cabina.setLayout(hboxTemperaturaCabina)
        
        hboxTemperaturaDucto1=QHBoxLayout()
        self.temperaturaDucto1=QLabel('{:0.1f}'.format(0))
        self.temperaturaDucto1.setFont(QFont("Sanserif",18))
        hboxTemperaturaDucto1.addWidget(self.temperaturaDucto1)
        grupo_temperatura_ducto1.setLayout(hboxTemperaturaDucto1)

        hboxTemperaturaDucto2=QHBoxLayout()
        self.temperaturaDucto2=QLabel('{:0.1f}'.format(0))
        self.temperaturaDucto2.setFont(QFont("Sanserif",18))
        hboxTemperaturaDucto2.addWidget(self.temperaturaDucto2)
        grupo_temperatura_ducto2.setLayout(hboxTemperaturaDucto2)
        
        seccion_temperaturas.addWidget(grupo_temperatura_cabina)
        seccion_temperaturas.addWidget(grupo_temperatura_ducto1)
        seccion_temperaturas.addWidget(grupo_temperatura_ducto2)
        
        #Seccion botones

        seccion_varias1=QHBoxLayout()
        seccion_varias2=QHBoxLayout()
        
        vboxoperaciones.addLayout(seccion_varias1)
        vboxoperaciones.addLayout(seccion_varias2)
        
        BotonIniciar=QPushButton("INICIAR")
        BotonIniciar.clicked.connect(self.iniciar)
        BotonIniciar.setIcon(QIcon('/home/pi/MAX6675/iconos/play.png'))
        BotonIniciar.setIconSize((QtCore.QSize(30,30)))
        BotonIniciar.setStyleSheet("color: #213142;" "font-family: Segoe UI;" "font-weight: bold")
        seccion_varias1.addWidget(BotonIniciar)

        BotonReset=QPushButton("RESET")
        BotonReset.clicked.connect(self.reset)
        BotonReset.setIcon(QIcon('/home/pi/MAX6675/iconos/reset.png'))
        BotonReset.setIconSize((QtCore.QSize(30,30)))
        BotonReset.setStyleSheet("color: #213142;" "font-family: Segoe UI;" "font-weight: bold")
        seccion_varias1.addWidget(BotonReset)

        BotonFinalizar=QPushButton("FINALIZAR")
        BotonFinalizar.clicked.connect(self.finalizar)
        BotonFinalizar.setIcon(QIcon('/home/pi/MAX6675/iconos/stop.png'))
        BotonFinalizar.setIconSize((QtCore.QSize(30,30)))
        BotonFinalizar.setStyleSheet("color: #213142;" "font-family: Segoe UI;" "font-weight: bold")
        seccion_varias1.addWidget(BotonFinalizar)

        BotonGuardarD=QPushButton("GUARDAR\nDATOS")
        BotonGuardarD.clicked.connect(self.guardarDatos)
        BotonGuardarD.setIcon(QIcon('/home/pi/MAX6675/iconos/csv.png'))
        BotonGuardarD.setIconSize((QtCore.QSize(30,30)))
        BotonGuardarD.setStyleSheet("color: #213142;" "font-family: Segoe UI;" "font-weight: bold")
        seccion_varias2.addWidget(BotonGuardarD)

        BotonGuardarG=QPushButton("GUARDAR\nGRÁFICA")
        BotonGuardarG.clicked.connect(self.guardarGrafica)
        BotonGuardarG.setIcon(QIcon('/home/pi/MAX6675/iconos/jpg.png'))
        BotonGuardarG.setIconSize((QtCore.QSize(30,30)))
        BotonGuardarG.setStyleSheet("color: #213142;" "font-family: Segoe UI;" "font-weight: bold")
        seccion_varias2.addWidget(BotonGuardarG)

        #Sección intervalos de medición

        hbox.addWidget(grupoGrafica)
        hbox.addWidget(grupoCalculos)
        
        grupoCalculos.setLayout(vboxoperaciones)
        grupoGrafica.setLayout(vboxgraficas)
        
        self.masas=[]
        self.tiempos=[]

        self.setLayout(hbox)
        
        self.f=QFile("Datos.csv")
        self.f.open(QIODevice.WriteOnly | QIODevice.Text)

        self.entrada=QTextStream(self.f)
        self.entrada <<"Tiempo(s),Masa(g)";
        self.entrada <<"\n";

        self.archivoRespaldo=open("archivoRespaldo.csv","w")
        self.archivoRespaldo.write("Tiempo(s),Masa(g)")
        self.archivoRespaldo.write("\n")
        self.archivoRespaldo.close()
        
        threadTemperatura=Temperatura(self)
        threadTemperatura.valorCambiado.connect(self.on_value_changed)
        
        self.threadMasa=CeldaCarga(self)
        self.threadMasa.nuevoValor.connect(self.cambiarValorMasa)
      
        threadTemperatura.start()
        self.threadMasa.start()
        self.indicador=False
        
    def on_value_changed(self,temp1,temp2,temp3):
        self.temperaturaCabina.setText('{:0.1f} °C'.format(temp1))
        self.temperaturaDucto1.setText('{:0.1f} °C'.format(temp2))
        self.temperaturaDucto2.setText('{:0.1f} °C'.format(temp3))
        
    def cambiarValorMasa(self,masa):
        self.masaCelda.setText('{:0.1f} g'.format(masa))

    def cambiarValorTiempo(self,tiempo):
        self.cronometro.setText('{}'.format(tiempo))

    def calibrar(self):
        self.indicador=False;
        CeldaCarga.hx.zero()
        
    def reset(self):
        pass
        if self.indicador==True:
            self.threadTemporizador.terminate()
            self.threadMasa=CeldaCarga(self)
            self.threadMasa.start()
            self.threadMasa.nuevoValor.connect(self.cambiarValorMasa)
            self.cronometro.setText('{}'.format("00:00:00"))
            self.masas=[]
            self.tiempos=[]
            self.plot.setData(self.tiempos,self.masas)
            self.indicador=False;
            if path.exists("archivoRespaldo.csv"):
                remove("archivoRespaldo.csv")
            
    def guardarArchivo(self,tiempo,masa):
        
        self.entrada <<tiempo;
        self.entrada <<",";
        self.entrada <<masa;
        self.entrada <<"\n";
        self.tiempos.append(tiempo)
        self.masas.append(masa)
        self.plot.setData(self.tiempos,self.masas)

        self.archivoRespaldo=open("archivoRespaldo.csv","a")
        self.archivoRespaldo.write(str(int(tiempo)))
        self.archivoRespaldo.write(",")
        self.archivoRespaldo.write(str(masa))
        self.archivoRespaldo.write("\n")
        self.archivoRespaldo.close()
        
    def opcion(self,opcion,string):
        if opcion==1:
            if path.exists("/media/pi/3C32-07A1"):
                shutil.copy('/home/pi/MAX6675/Datos.csv','/media/pi/3C32-07A1/Datos.csv')
        if opcion==2:
            
            is_valid=validate_email(string)
            now=datetime.now()
            fecha=str(now.date())
            remitente = 'secadorudeaoriente@gmail.com'
            destinatarios = [string]
            
            if is_valid==True:
                try:
                    request=requests.get("http://www.google.com?",timeout=5)
                except(requests.ConnectionError,requests.Timeout):
                    print("sin conexion")
                else:
                    
                    asunto = 'Datos secado '+fecha
                    cuerpo = 'Datos experimento de secado'
                    ruta_adjunto = 'Datos.csv'
                    nombre_adjunto = 'Datos.csv'
                    mensaje = MIMEMultipart()
                    mensaje['From'] = remitente
                    mensaje['To'] = ", ".join(destinatarios)
                    mensaje['Subject'] = asunto
                    mensaje.attach(MIMEText(cuerpo, 'plain'))
                    archivo_adjunto = open(ruta_adjunto, 'rb')
                    adjunto_MIME = MIMEBase('application', 'octet-stream')
                    adjunto_MIME.set_payload((archivo_adjunto).read())
                    encoders.encode_base64(adjunto_MIME)
                    adjunto_MIME.add_header('Content-Disposition', "attachment; filename= %s" % nombre_adjunto)
                    mensaje.attach(adjunto_MIME)
                    sesion_smtp = smtplib.SMTP('smtp.gmail.com', 587)
                    sesion_smtp.starttls()
                    sesion_smtp.login('secadorudeaoriente@gmail.com','Secador2021Oriente')
                    texto = mensaje.as_string()
                    sesion_smtp.sendmail(remitente, destinatarios, texto)
                    sesion_smtp.quit()
                
    def opcion2(self,opcion,string):
        if opcion==1:
            if path.exists("/media/pi/3C32-07A1"):
                shutil.copy('/home/pi/MAX6675/grafica.png','/media/pi/3C32-07A1/grafica.png')
            
        if opcion==2:
            
            is_valid=validate_email(string)
            now=datetime.now()
            fecha=str(now.date())
            remitente = 'secadorudeaoriente@gmail.com'
            destinatarios = [string]
            
            if is_valid==True:
                try:
                    request=requests.get("http://www.google.com?",timeout=5)
                except(requests.ConnectionError,requests.Timeout):
                    print()
                else:
                    
                    asunto = 'Gráfica secado '+fecha
                    cuerpo = 'Curva experimento de secado'
                    ruta_adjunto = 'grafica.png'
                    nombre_adjunto = 'grafica.png'
                    mensaje = MIMEMultipart()
                    mensaje['From'] = remitente
                    mensaje['To'] = ", ".join(destinatarios)
                    mensaje['Subject'] = asunto
                    mensaje.attach(MIMEText(cuerpo, 'plain'))
                    archivo_adjunto = open(ruta_adjunto, 'rb')
                    adjunto_MIME = MIMEBase('application', 'octet-stream')
                    adjunto_MIME.set_payload((archivo_adjunto).read())
                    encoders.encode_base64(adjunto_MIME)
                    adjunto_MIME.add_header('Content-Disposition', "attachment; filename= %s" % nombre_adjunto)
                    mensaje.attach(adjunto_MIME)
                    sesion_smtp = smtplib.SMTP('smtp.gmail.com', 587)
                    sesion_smtp.starttls()
                    sesion_smtp.login('secadorudeaoriente@gmail.com','Secador2021Oriente')
                    texto = mensaje.as_string()
                    sesion_smtp.sendmail(remitente, destinatarios, texto)
                    sesion_smtp.quit()
                
    def guardarDatos(self):
        self.f.close()
        self.window=guardarDatos()
        self.window.show()
        
        self.window.valor2.connect(self.opcion)
    
    def iniciar(self):
        
        if self.indicador!=True:
            
            self.threadMasa.terminate()
            self.threadTemporizador=Temporizador(self)
            self.threadTemporizador.tiempoMasa.connect(self.guardarArchivo)
            self.threadTemporizador.valorTiempo.connect(self.cambiarValorTiempo)
            self.threadTemporizador.valorMasa.connect(self.cambiarValorMasa)
            self.threadTemporizador.start()
            self.indicador=True
        
    def guardarGrafica(self):
        
        exporter = pg.exporters.ImageExporter(self.graphWidget.plotItem)
        exporter.export('grafica.png')
        self.window=guardarGraficaPpal()
        self.window.show()
        
        self.window.valor2.connect(self.opcion2)
        
    def finalizar(self):
        if self.indicador==False:
            pass
        else:
            self.threadTemporizador.terminate()
    
class Graficas_VS (QWidget):
    def __init__(self):
        super().__init__()
        vbox=QVBoxLayout()
        hbox=QHBoxLayout()
        grupoGraficaVS=QGroupBox("Curva velocidad de secado base seca")
        hbox.addWidget(grupoGraficaVS)
        self.graphWidget1 = pg.PlotWidget()
        self.plot1=self.graphWidget1.plot()
        self.graphWidget1.setLabel(axis='left', text='Velocidad de secado')
        self.graphWidget1.setLabel(axis='bottom', text='% Humedad')
        self.graphWidget1.setTitle("Velocidad de secado Base humeda")
        vboxgrafica1=QVBoxLayout()
        vboxgrafica1.addWidget(self.graphWidget1)
        grupoGraficaVS.setLayout(vboxgrafica1)
        
        grupoGraficaVSBS=QGroupBox("Curva velocidad de secado base seca")
        hbox.addWidget(grupoGraficaVSBS)
        self.graphWidget2 = pg.PlotWidget()
        self.plot2=self.graphWidget2.plot()
        self.graphWidget2.setLabel(axis='left', text='Velocidad de secado')
        self.graphWidget2.setLabel(axis='bottom', text='% Humedad')
        self.graphWidget2.setTitle("Velocidad de secado Base seca")
        vboxgrafica2=QVBoxLayout()
        vboxgrafica2.addWidget(self.graphWidget2)
        grupoGraficaVSBS.setLayout(vboxgrafica2)
        vbox.addLayout(hbox)
     
        hbox3=QHBoxLayout()
        grupoParametros=QGroupBox("Parámetros")
        humedadLabel=QLabel("%Humedad")
        self.humedad=QLineEdit()
        self.humedad.setValidator(QDoubleValidator(0.00,100.00,2))
        areaLabel=QLabel("Área (m<sup>2</sup>)")
        self.area=QLineEdit()
        self.area.setValidator(QDoubleValidator(0.00,10000000000.00,2))
        hbox33=QHBoxLayout()
        hbox33.addWidget(humedadLabel)
        hbox33.addWidget(self.humedad)
        hbox33.addWidget(areaLabel)
        hbox33.addWidget(self.area)
        
        grupoParametros.setLayout(hbox33)
        hbox3.addWidget(grupoParametros)
        vbox.addLayout(hbox3)        

        hbox4=QHBoxLayout()
        BotonGuardarGenerar=QPushButton("GENERAR GRÁFICAS")
        BotonGuardarGenerar.clicked.connect(self.graficas)
        BotonGuardarGenerar.setIcon(QIcon('/home/pi/MAX6675/iconos/generateGraph.png'))
        BotonGuardarGenerar.setIconSize((QtCore.QSize(38,38)))
        BotonGuardarGenerar.setStyleSheet("color: #213142;" "font-family: Segoe UI;" "font-weight: bold")
        hbox4.addWidget(BotonGuardarGenerar)
        
        BotonGuardarGra=QPushButton("GUARDAR GRÁFICAS")
        BotonGuardarGra.clicked.connect(self.guardarGrafica)
        BotonGuardarGra.setIcon(QIcon('/home/pi/MAX6675/iconos/jpg.png'))
        BotonGuardarGra.setIconSize((QtCore.QSize(38,38)))
        BotonGuardarGra.setStyleSheet("color: #213142;" "font-family: Segoe UI;" "font-weight: bold")
        hbox4.addWidget(BotonGuardarGra)
        vbox.addLayout(hbox4)
        self.setLayout(vbox)


    def graficas(self):
        
            
        hum=float(self.humedad.text())/100
        are=float(self.area.text())
        
        archivo=open('Datos.csv')
        archivo.readline()
        masas=[]
        datosHumH=[]
        datosHumS=[]
        datosVel=[]
        tiempos=[]
        for x in archivo:
            linea=list(x.split(","))
            masas.append(float(linea[1].rstrip('\n')))
            tiempos.append(float(linea[0]))
            
        if len(masas)!=0:
            mInicial=masas[0]
            mS=mInicial*(1-hum)
            
            for z in masas:
                datosHumH.append((z-mS)/z*100)
                datosHumS.append((z-mS)/mS)
            for y in range(1,len(datosHumS)):
                datosVel.append(float(mS*(datosHumS[0]-datosHumS[y]))/(tiempos[y]*are))
            self.plot1.setData(tiempos,datosHumH)
            self.plot2.setData(tiempos,datosHumS)


    def guardarGrafica(self):
        
        exporter = pg.exporters.ImageExporter(self.graphWidget1.plotItem)
        exporter.export('Velocidad Secado BH.png')

        exporter2 = pg.exporters.ImageExporter(self.graphWidget2.plotItem)
        exporter2.export('Velocidad Secado BS.png')
        self.window=guardarGraficasVS()
        self.window.show()
        
        self.window.valor2.connect(self.opcion2)
        
    def opcion2(self,opcion,string):
        if opcion==1:
            if path.exists("/media/pi/3C32-07A1"):
                shutil.copy('/home/pi/MAX6675/Velocidad Secado BS.png','/media/pi/3C32-07A1/Velocidad Secado BS.png')
                shutil.copy('/home/pi/MAX6675/Velocidad Secado BH.png','/media/pi/3C32-07A1/Velocidad Secado BH.png')
        if opcion==2:
            
            is_valid=validate_email(string)
            now=datetime.now()
            fecha=str(now.date())
            remitente = 'secadorudeaoriente@gmail.com'
            destinatarios = [string]
            
            if is_valid==True:
                try:
                    request=requests.get("http://www.google.com?",timeout=5)
                except(requests.ConnectionError,requests.Timeout):
                    print()
                else:
                    asunto = 'Gráficas velocidad de secado base húmeda '+fecha
                    cuerpo = 'Curva velocidades de secado base húmeda'
                    ruta_adjunto = 'Velocidad Secado BH.png'
                    nombre_adjunto = 'Velocidad Secado BH.png'
                    mensaje = MIMEMultipart()
                    mensaje['From'] = remitente
                    mensaje['To'] = ", ".join(destinatarios)
                    mensaje['Subject'] = asunto
                    mensaje.attach(MIMEText(cuerpo, 'plain'))
                    archivo_adjunto = open(ruta_adjunto, 'rb')
                    adjunto_MIME = MIMEBase('application', 'octet-stream')
                    adjunto_MIME.set_payload((archivo_adjunto).read())
                    encoders.encode_base64(adjunto_MIME)
                    adjunto_MIME.add_header('Content-Disposition', "attachment; filename= %s" % nombre_adjunto)
                    mensaje.attach(adjunto_MIME)
                    sesion_smtp = smtplib.SMTP('smtp.gmail.com', 587)
                    sesion_smtp.starttls()
                    sesion_smtp.login('secadorudeaoriente@gmail.com','Secador2021Oriente')
                    texto = mensaje.as_string()
                    sesion_smtp.sendmail(remitente, destinatarios, texto)
                    sesion_smtp.quit()


                    asunto = 'Gráficas velocidad de secado base seca '+fecha
                    cuerpo = 'Curva velocidades de secado base seca'
                    ruta_adjunto = 'Velocidad Secado BS.png'
                    nombre_adjunto = 'Velocidad Secado BS.png'
                    mensaje = MIMEMultipart()
                    mensaje['From'] = remitente
                    mensaje['To'] = ", ".join(destinatarios)
                    mensaje['Subject'] = asunto
                    mensaje.attach(MIMEText(cuerpo, 'plain'))
                    archivo_adjunto = open(ruta_adjunto, 'rb')
                    adjunto_MIME = MIMEBase('application', 'octet-stream')
                    adjunto_MIME.set_payload((archivo_adjunto).read())
                    encoders.encode_base64(adjunto_MIME)
                    adjunto_MIME.add_header('Content-Disposition', "attachment; filename= %s" % nombre_adjunto)
                    mensaje.attach(adjunto_MIME)
                    sesion_smtp = smtplib.SMTP('smtp.gmail.com', 587)
                    sesion_smtp.starttls()
                    sesion_smtp.login('secadorudeaoriente@gmail.com','Secador2021Oriente')
                    texto = mensaje.as_string()
                    sesion_smtp.sendmail(remitente, destinatarios, texto)
                    sesion_smtp.quit()  

class Graficas_H (QWidget):
    def __init__(self):
        super().__init__()
        vbox=QVBoxLayout()

        hbox2=QHBoxLayout()
        grupoGraficaCHBH=QGroupBox("Curva de humedad en base humeda")
        hbox2.addWidget(grupoGraficaCHBH)
        self.graphWidget3 = pg.PlotWidget()
        self.plot3=self.graphWidget3.plot()
        self.graphWidget3.setLabel(axis='left', text='Humedad Base Humeda')
        self.graphWidget3.setLabel(axis='bottom', text='Tiempo (s)')
        self.graphWidget3.setTitle("Humedad vs Tiempo")
        vboxgrafica3=QVBoxLayout()
        vboxgrafica3.addWidget(self.graphWidget3)
        grupoGraficaCHBH.setLayout(vboxgrafica3)
        
        grupoGraficaCHBS=QGroupBox("Curva de humedad en base seca")
        hbox2.addWidget(grupoGraficaCHBS)
        self.graphWidget4 = pg.PlotWidget()
        self.plot4=self.graphWidget4.plot()
        self.graphWidget4.setLabel(axis='left', text='Humedad Base Seca')
        self.graphWidget4.setLabel(axis='bottom', text='Tiempo (s)')
        self.graphWidget4.setTitle("Humedad vs Tiempo")
        vboxgrafica4=QVBoxLayout()
        vboxgrafica4.addWidget(self.graphWidget4)
        grupoGraficaCHBS.setLayout(vboxgrafica4)
        vbox.addLayout(hbox2)
        
        hbox3=QHBoxLayout()
        grupoParametros=QGroupBox("Parámetros")
        humedadLabel=QLabel("%Humedad")
        self.humedad=QLineEdit()
        self.humedad.setValidator(QDoubleValidator(0.00,100.00,2))
        hbox33=QHBoxLayout()
        hbox33.addWidget(humedadLabel)
        hbox33.addWidget(self.humedad)

        grupoParametros.setLayout(hbox33)
        hbox3.addWidget(grupoParametros)
        vbox.addLayout(hbox3)        

        hbox4=QHBoxLayout()
        BotonGuardarGenerar=QPushButton("GENERAR GRÁFICAS")
        BotonGuardarGenerar.clicked.connect(self.graficas)
        BotonGuardarGenerar.setIcon(QIcon('/home/pi/MAX6675/iconos/generateGraph.png'))
        BotonGuardarGenerar.setIconSize((QtCore.QSize(38,38)))
        BotonGuardarGenerar.setStyleSheet("color: #213142;" "font-family: Segoe UI;" "font-weight: bold")
        hbox4.addWidget(BotonGuardarGenerar)
        
        BotonGuardarGra=QPushButton("GUARDAR GRÁFICAS")
        BotonGuardarGra.clicked.connect(self.guardarGrafica)
        BotonGuardarGra.setIcon(QIcon('/home/pi/MAX6675/iconos/jpg.png'))
        BotonGuardarGra.setIconSize((QtCore.QSize(38,38)))
        BotonGuardarGra.setStyleSheet("color: #213142;" "font-family: Segoe UI;" "font-weight: bold")
        hbox4.addWidget(BotonGuardarGra)
        vbox.addLayout(hbox4)

        self.setLayout(vbox)
 

    def graficas(self):
        
            
        hum=float(self.humedad.text())/100
        are=float(self.area.text())
        
        archivo=open('Datos.csv')
        archivo.readline()
        masas=[]
        datosHumH=[]
        datosHumS=[]
        datosVel=[]
        tiempos=[]
        for x in archivo:
            linea=list(x.split(","))
            masas.append(float(linea[1].rstrip('\n')))
            tiempos.append(float(linea[0]))
            
        if len(masas)!=0:
            mInicial=masas[0]
            mS=mInicial*(1-hum)
            
            for z in masas:
                datosHumH.append((z-mS)/z*100)
                datosHumS.append((z-mS)/mS)
            for y in range(1,len(datosHumS)):
                datosVel.append(float(mS*(datosHumS[0]-datosHumS[y]))/(tiempos[y]*are))
            self.plot3.setData(datosHumS[1:],datosVel)
            self.plot4.setData(tiempos[1:],datosVel)

    def guardarGrafica(self):
        exporter3= pg.exporters.ImageExporter(self.graphWidget3.plotItem)
        exporter3.export('Humedad BH.png')
        
        exporter4= pg.exporters.ImageExporter(self.graphWidget4.plotItem)
        exporter4.export('Humedad BS.png')
        self.window=guardarGraficasH()
        self.window.show()
        
        self.window.valor2.connect(self.opcion2)

    def opcion2(self,opcion,string):
        if opcion==1:
            if path.exists("/media/pi/3C32-07A1"):          
                shutil.copy('/home/pi/MAX6675/Humedad BH.png','/media/pi/3C32-07A1/Humedad BH.png')
                shutil.copy('/home/pi/MAX6675/Humedad BS.png','/media/pi/3C32-07A1/Humedad BS.png')
        if opcion==2:
            
            is_valid=validate_email(string)
            now=datetime.now()
            fecha=str(now.date())
            remitente = 'secadorudeaoriente@gmail.com'
            destinatarios = [string]
            
            if is_valid==True:
                try:
                    request=requests.get("http://www.google.com?",timeout=5)
                except(requests.ConnectionError,requests.Timeout):
                    print()
                else:
                    asunto = 'Gráficas % humedad base húmeda '+fecha
                    cuerpo = 'Curva % humedad base húmeda secado'
                    ruta_adjunto = 'Humedad BH.png.png'
                    nombre_adjunto = 'Humedad BH.png.png'
                    mensaje = MIMEMultipart()
                    mensaje['From'] = remitente
                    mensaje['To'] = ", ".join(destinatarios)
                    mensaje['Subject'] = asunto
                    mensaje.attach(MIMEText(cuerpo, 'plain'))
                    archivo_adjunto = open(ruta_adjunto, 'rb')
                    adjunto_MIME = MIMEBase('application', 'octet-stream')
                    adjunto_MIME.set_payload((archivo_adjunto).read())
                    encoders.encode_base64(adjunto_MIME)
                    adjunto_MIME.add_header('Content-Disposition', "attachment; filename= %s" % nombre_adjunto)
                    mensaje.attach(adjunto_MIME)
                    sesion_smtp = smtplib.SMTP('smtp.gmail.com', 587)
                    sesion_smtp.starttls()
                    sesion_smtp.login('secadorudeaoriente@gmail.com','Secador2021Oriente')
                    texto = mensaje.as_string()
                    sesion_smtp.sendmail(remitente, destinatarios, texto)
                    sesion_smtp.quit()


                    asunto = 'Gráficas % humedad base seca '+fecha
                    cuerpo = 'Curva % humedad base seca secado'
                    ruta_adjunto = 'Humedad BS.png.png'
                    nombre_adjunto = 'Humedad BS.png.png'
                    mensaje = MIMEMultipart()
                    mensaje['From'] = remitente
                    mensaje['To'] = ", ".join(destinatarios)
                    mensaje['Subject'] = asunto
                    mensaje.attach(MIMEText(cuerpo, 'plain'))
                    archivo_adjunto = open(ruta_adjunto, 'rb')
                    adjunto_MIME = MIMEBase('application', 'octet-stream')
                    adjunto_MIME.set_payload((archivo_adjunto).read())
                    encoders.encode_base64(adjunto_MIME)
                    adjunto_MIME.add_header('Content-Disposition', "attachment; filename= %s" % nombre_adjunto)
                    mensaje.attach(adjunto_MIME)
                    sesion_smtp = smtplib.SMTP('smtp.gmail.com', 587)
                    sesion_smtp.starttls()
                    sesion_smtp.login('secadorudeaoriente@gmail.com','Secador2021Oriente')
                    texto = mensaje.as_string()
                    sesion_smtp.sendmail(remitente, destinatarios, texto)
                    sesion_smtp.quit()

class pantallaInicio(QDialog):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("SECADOR CONVECTIVO")
        self.setGeometry(200,100,0,0)
        self.setFixedSize(450,330)
        self.vbox=QVBoxLayout()
        titulo=QLabel("MODULO ADQUISICIÓN DE DATOS")
        titulo.setStyleSheet("color: #213142;" "font-family: Segoe UI;" "font-weight: bold")
        titulo.setAlignment(Qt.AlignCenter)
        titulo2=QLabel("SECADOR CONVECTIVO")
        titulo2.setStyleSheet("color: #213142;" "font-family: Segoe UI;" "font-weight: bold")
        titulo2.setAlignment(Qt.AlignCenter)
        imagen=QPixmap('/home/pi/MAX6675/iconos/udea.png').scaled(300,150,Qt.KeepAspectRatio)
        labelImage=QLabel()
        labelImage.setPixmap(imagen)
        self.vbox.addWidget(labelImage)
        self.vbox.addWidget(titulo)
        self.vbox.addWidget(titulo2)
        
        labelImage.setAlignment(Qt.AlignCenter)
        creditos=QLabel("Realizado por:")
        nombre=QLabel("Estefanía Cardona Castro")
        asesores=QLabel("Asesorado por:")
        nombre2=QLabel("Andrés Felipe Castaño Franco")
        nombre3=QLabel("Helber Andrés Carvajal Castaño")
        creditos.setAlignment(Qt.AlignCenter)
        nombre.setAlignment(Qt.AlignCenter)
        asesores.setAlignment(Qt.AlignCenter)
        nombre2.setAlignment(Qt.AlignCenter)
        nombre3.setAlignment(Qt.AlignCenter)
        self.vbox.addWidget(creditos)
        self.vbox.addWidget(nombre)
        self.vbox.addWidget(asesores)
        self.vbox.addWidget(nombre2)
        self.vbox.addWidget(nombre3)
        
        hbox=QHBoxLayout()
        
        self.vbox.addLayout(hbox)
        
        self.setLayout(self.vbox)
               
class guardarDatos(QWidget):
    cor=""
    valor2=pyqtSignal(int,str)
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Guardar Datos")
        self.setGeometry(245,253,0,200)
        self.vbox=QVBoxLayout()
        pregunta=QLabel("¿Dónde desea guardar los datos del experimento?")
        botonUSB=QPushButton("USB")
        botonCorreo=QPushButton("Correo")
        botonUSB.clicked.connect(self.usb)
        botonCorreo.clicked.connect(self.correo)
        self.vbox.addWidget(pregunta)
        hbox=QHBoxLayout()
        hbox.addWidget(botonUSB)
        hbox.addWidget(botonCorreo)
        self.vbox.addLayout(hbox)
        self.correo=QLineEdit()
        self.setLayout(self.vbox)

    def usb(self):
        self.valor2.emit(1,"nada")
        self.close()
    def correo(self):
        
        self.vbox.addWidget(self.correo)
        botonEnviar=QPushButton("Enviar")
        self.vbox.addWidget(botonEnviar)
        
        botonEnviar.clicked.connect(self.enviar)
        
            
    def enviar(self):
        
        self.cor=str(self.correo.text())
        self.valor2.emit(2,self.cor)
        self.close()

class guardarGraficaPpal(QWidget):
    cor=""
    valor2=pyqtSignal(int,str)
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Guardar Datos")
        self.setGeometry(245,253,0,200)
        self.vbox=QVBoxLayout()
        pregunta=QLabel("¿Dónde desea guardar los datos del experimento?")
        botonUSB=QPushButton("USB")
        botonCorreo=QPushButton("Correo")
        botonUSB.clicked.connect(self.usb)
        botonCorreo.clicked.connect(self.correo)
        self.vbox.addWidget(pregunta)
        hbox=QHBoxLayout()
        hbox.addWidget(botonUSB)
        hbox.addWidget(botonCorreo)
        self.vbox.addLayout(hbox)
        self.correo=QLineEdit()
        self.setLayout(self.vbox)

    def usb(self):
        self.valor2.emit(1,"nada")
        self.close()
    def correo(self):
        self.vbox.addWidget(self.correo)
        botonEnviar=QPushButton("Enviar")
        self.vbox.addWidget(botonEnviar)
        botonEnviar.clicked.connect(self.enviar)
        
    def enviar(self):
        self.cor=str(self.correo.text())
        self.valor2.emit(2,self.cor)
        self.close()

class guardarGraficasH(QWidget):
    cor=""
    valor2=pyqtSignal(int,str)
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Guardar Datos")
        self.setGeometry(245,253,0,200)
        self.vbox=QVBoxLayout()
        pregunta=QLabel("¿Dónde desea guardar los datos del experimento?")
        botonUSB=QPushButton("USB")
        botonCorreo=QPushButton("Correo")
        botonUSB.clicked.connect(self.usb)
        botonCorreo.clicked.connect(self.correo)
        self.vbox.addWidget(pregunta)
        hbox=QHBoxLayout()
        hbox.addWidget(botonUSB)
        hbox.addWidget(botonCorreo)
        self.vbox.addLayout(hbox)
        self.correo=QLineEdit()
        self.setLayout(self.vbox)

    def usb(self):
        self.valor2.emit(1,"nada")
        self.close()
    def correo(self):
        self.vbox.addWidget(self.correo)
        botonEnviar=QPushButton("Enviar")
        self.vbox.addWidget(botonEnviar)
        botonEnviar.clicked.connect(self.enviar)
        
            
    def enviar(self):
        self.cor=str(self.correo.text())
        self.valor2.emit(2,self.cor)
        self.close()

class guardarGraficasVS(QWidget):
    cor=""
    valor2=pyqtSignal(int,str)
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Guardar Datos")
        self.setGeometry(245,253,0,200)
        self.vbox=QVBoxLayout()
        pregunta=QLabel("¿Dónde desea guardar los datos del experimento?")
        botonUSB=QPushButton("USB")
        botonCorreo=QPushButton("Correo")
        botonUSB.clicked.connect(self.usb)
        botonCorreo.clicked.connect(self.correo)
        self.vbox.addWidget(pregunta)
        hbox=QHBoxLayout()
        hbox.addWidget(botonUSB)
        hbox.addWidget(botonCorreo)
        self.vbox.addLayout(hbox)
        self.correo=QLineEdit()
        self.setLayout(self.vbox)

    def usb(self):
        self.valor2.emit(1,"nada")
        self.close()
    def correo(self):
        self.vbox.addWidget(self.correo)
        botonEnviar=QPushButton("Enviar")
        self.vbox.addWidget(botonEnviar)
        botonEnviar.clicked.connect(self.enviar)
        
            
    def enviar(self):
        self.cor=str(self.correo.text())
        self.valor2.emit(2,self.cor)
        self.close()

class transmitirDatos(QWidget):
    
    def __init__(self):
        super().__init__()
        vbox=QVBoxLayout()
        BotonTransmision=QPushButton("Transmitir datos remotamente")
        BotonTransmision.clicked.connect(self.transmitir)
        vbox.addWidget(BotonTransmision)
        self.setLayout(vbox)
        
    def transmitir(self):
        webbrowser.open('meet.google.com/djn-bmok-rpd',new=2)

class apagar(QWidget):
    def __init__(self):
        super().__init__()
        vbox=QVBoxLayout()
        BotonTransmision=QPushButton("Apagar módulo adquisición de datos")
        BotonTransmision.clicked.connect(self.apagado)
        vbox.addWidget(BotonTransmision)
        self.setLayout(vbox)
        
    def apagado(self):
        os.system("sudo shutdown -h now")    
    
if __name__ == '__main__':
    app = QApplication(sys.argv)
    window=Interfaz()
    sys.exit(app.exec_())
