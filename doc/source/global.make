# global things needed by all make files -- mostly meta rules

SHELL = ksh

# allows the use of ../ in include statements
env = openout_any=a openin_any=a

%.pdf : %.tex
	$(env) latex -halt-on-error -interaction=nonstopmode -output-format=pdf $<

%.dvi : %.tex
	$(env) latex -halt-on-error -interaction=nonstopmode -output-format=dvi $<

# xfig used to produce/maintain figures. this converts to eps
%.eps: %.fig
	fig2dev -L eps <$< >$@

