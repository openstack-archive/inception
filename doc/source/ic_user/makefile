# vim:sw=4 ts=4:

# Abstract:	makes all pdf files. make promote will copy the final .pdf files to the top level source
#			make clean cleans up tex detritus, make nuke scrubs everything away.
# Date: 	26 August 2013
# Requires:	TeX 3.1415926 (TeX Live 2013), fig2dev
# Mods:
#

include ../global.make	# meta stuff

#	we'll default to bash -- if no MK_SHELL was supplied we'll assume a sparse system that doesn't have ksh either; sigh.
ifeq ($(SHELL),sh)
	MODERN_SHELL := bash
endif

fig_list = inception_final start_overview inception_planes
sec_list = overview prep running using examples orch_cmdline
dyn_list = dyn_cmdline

build_list = ic_user.pdf
all:: $(build_list)



# generate the body of the command line options section
.PHONY: dyn_cmdline.tex
dyn_cmdline.tex:
	$(MODERN_SHELL) gen_cmdline_tex.ksh inception/orchestrator.py  dyn_cmdline.tex orchestrator_opts
	
	
promote:	$(build_list)
	for f in $(build_list);\
	do\
		cp $$f ../;\
	done

ic_user.pdf: ic_user.tex $(sec_list:%=%.tex) $(dyn_list:%=%.tex) $(fig_list:%=%.pdf)

# everything except final doc files
clean:
	rm -f  $(fig_list:%=%.pdf)  *.eps *.aux *.log || true

# everything except the source
nuke:
	rm -f $(build_list) $(fig_list:%=%.pdf)  *.eps *.aux *.log || true
