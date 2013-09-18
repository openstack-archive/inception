# global things needed by all make files -- mostly meta rules

# allow user to override with better shell when desired.
# unfortunately (g)make overrides SHELL rather than importing it; pull from MK_SHELL if set
ifneq ($(MK_SHELL),)
	SHELL := $(MK_SHELL)
else
	SHELL := sh
endif


# allows the use of ../ in include statements
env = openout_any=a openin_any=a

%.pdf : %.tex
	$(env) latex -halt-on-error -interaction=nonstopmode -output-format=pdf $<

%.dvi : %.tex
	$(env) latex -halt-on-error -interaction=nonstopmode -output-format=dvi $<

# xfig used to produce/maintain figures. Thes convert to usable formats.
%.eps: %.fig
	fig2dev -L eps <$< >$@

%.pdf: %.fig
	fig2dev -L pdf <$< >$@
