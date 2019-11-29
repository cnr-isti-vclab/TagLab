QT -= gui

CONFIG += c++11 console
CONFIG -= app_bundle


DEFINES += QT_DEPRECATED_WARNINGS

SOURCES += \
        src/coraline.cpp \
        src/coralinepy.cpp \
        src/getopt.cpp \
        src/main.cpp \
        src/maxflow/graph.cpp

# Default rules for deployment.
qnx: target.path = /tmp/$${TARGET}/bin
else: unix:!android: target.path = /opt/$${TARGET}/bin
!isEmpty(target.path): INSTALLS += target

HEADERS += \
    src/coraline.h \
    src/getopt.h \
    src/maxflow/graph.h

DISTFILES += \
    Coraline.py
