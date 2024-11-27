prepare: prepare.cpp
	mkdir -p bin
	$(CXX) -std=c++11 -o bin/prepare prepare.cpp
