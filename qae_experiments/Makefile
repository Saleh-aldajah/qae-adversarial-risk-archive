.PHONY: fast all hash cert minimax single rc hardware docker-build docker-fast docker-all

fast:
	python reproduce_fast.py

all:
	python reproduce_all.py

hash:
	python verify_hashes.py

cert:
	python verify_certificate.py

minimax:
	python generate_minimax_bounds.py

single:
	python run_single_round_only.py

rc:
	python run_rc_only.py

hardware:
	python run_hardware_ablations.py

docker-build:
	docker build -t qae-v16-reproduce .

docker-fast: docker-build
	docker run --rm qae-v16-reproduce python reproduce_fast.py

docker-all: docker-build
	docker run --rm qae-v16-reproduce python reproduce_all.py
