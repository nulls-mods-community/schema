.PHONY: all
all: | clean build

.PHONY: build
build: build.py schema.json meta.schema.json patches.schema.json
	python3 $<

.PHONY: generate
generate: generate.py
	python3 $<

.PHONY: clean
clean:
	rm -rf build/
	rm -rf generated/