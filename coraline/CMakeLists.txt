cmake_minimum_required(VERSION 3.1)
project(coraline)

SET(CORALINE_SOURCE_PATH src)
SET(MAXFLOW_SOURCE_PATH src/maxflow)

SET(LIB_HEADERS
	${CORALINE_SOURCE_PATH}/coraline.h
	${MAXFLOW_SOURCE_PATH}/block.h
	${MAXFLOW_SOURCE_PATH}/graph.h
	${MAXFLOW_SOURCE_PATH}/graph.cpp
)

SET(LIB_SOURCES
	${CORALINE_SOURCE_PATH}/coraline.cpp
	${CORALINE_SOURCE_PATH}/coralinepy.cpp
	${CORALINE_SOURCE_PATH}/maxflow.cpp
)

SET(EXE_SOURCE
	${CORALINE_SOURCE_PATH}/main.cpp
	${CORALINE_SOURCE_PATH}/getopt.cpp
	${CORALINE_SOURCE_PATH}/coraline.cpp
	${CORALINE_SOURCE_PATH}/maxflow.cpp
)

SET(EXE_HEADERS
	${CORALINE_SOURCE_PATH}/getopt.h
	${CORALINE_SOURCE_PATH}/coraline.h
	${MAXFLOW_SOURCE_PATH}/block.h
	${MAXFLOW_SOURCE_PATH}/graph.h
	${MAXFLOW_SOURCE_PATH}/graph.cpp
)

ADD_LIBRARY(coralinelib SHARED ${LIB_SOURCES} ${LIB_HEADERS})
ADD_EXECUTABLE(coralineexe ${EXE_SOURCE} ${EXE_HEADERS})

SET(CORALINE_DEFINITIONS "") 

if(MSVC)
	SET(CORALINE_CFLAGS /nologo /W3)
	LIST(APPEND CORALINE_DEFINITIONS _CRT_SECURE_NO_DEPRECATE)
else()
	SET(CORALINE_CFLAGS -O2 -W -Wall -c -std=c++11 -pedantic)
endif()

SET(CORALINEEXE_CFLAGS ${CORALINE_CFLAGS})
SET(CORALINELIB_CFLAGS ${CORALINE_CFLAGS})

if("${CMAKE_SYSTEM_NAME}" MATCHES "Linux")
	LIST(APPEND CORALINELIB_CFLAGS -fPIC)
elseif(APPLE)
	LIST(APPEND CORALINELIB_CFLAGS -fvisibility=hidden)
	if(IOS)
		LIST(APPEND CORALINELIB_CFLAGS -fembed-bitcode)
		set_xcode_property(coralinelib IPHONEOS_DEPLOYMENT_TARGET "9.2")
		set_xcode_property(coralineexe IPHONEOS_DEPLOYMENT_TARGET "9.2")
	endif(IOS)
endif()

target_include_directories(coralinelib PUBLIC ${CORALINE_SOURCE_PATH})
target_include_directories(coralineexe PUBLIC ${CORALINE_SOURCE_PATH})

target_link_libraries(coralineexe PUBLIC coralinelib)

target_compile_definitions(coralinelib PUBLIC ${CORALINE_DEFINITIONS})
target_compile_options    (coralinelib PUBLIC ${CORALINELIB_CFLAGS})
target_compile_options    (coralineexe PUBLIC ${CORALINEEXE_CFLAGS})
set_target_properties     (coralinelib PROPERTIES DEBUG_POSTFIX "d")
set_target_properties     (coralineexe PROPERTIES OUTPUT_NAME "coraline")
set_target_properties     (coralinelib PROPERTIES OUTPUT_NAME "coraline")

INSTALL(TARGETS coralinelib coralineexe
	RUNTIME DESTINATION bin
	BUNDLE DESTINATION bin
	LIBRARY DESTINATION lib
	ARCHIVE DESTINATION lib)

