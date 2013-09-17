# 
# Abstract:	makes all pdf files. make promote will copy the final .pdf files to the top level source
#			make clean cleans up tex detritus, make nuke scrubs everything away.
# Date: 	26 August 2013
# Requires:	TeX 3.1415926 (TeX Live 2013), fig2dev
# Mods:
#

include ../global.make	# meta stuff

fig_list = inception_final start_overview inception_planes
sec_list = overview prep running using examples


build_list = ic_user.pdf
all:: $(build_list)

promote::	$(build_list)
	for f in $(build_list);\
	do\
		cp $$f ../;\
	done

ic_user.pdf:: ic_user.tex $(sec_list:%=%.tex) $(fig_list:%=%.eps)

# everything except final doc files
clean:
	rm -f  *converted-to.pdf *.eps *.aux *.log || true

# everything except the source
nuke:
	rm -f $(build_list) *converted-to.pdf *.eps *.aux *.log || true
