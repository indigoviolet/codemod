.PHONY: test install pep8 release clean

test: pep8
	py.test --doctest-modules modone

install:
	python setup.py develop

pep8:
	@flake8 modone --ignore=F403

release: test
	@python setup.py sdist upload

clean:
	@find ./ -name '*.pyc' -exec rm -f {} \;
	@find ./ -name 'Thumbs.db' -exec rm -f {} \;
	@find ./ -name '*~' -exec rm -f {} \;
