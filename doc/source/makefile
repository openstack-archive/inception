# simple makefile to build all doc from the subdirectories below and to 
# pull the final pdf files to this directory.

sub_dirs = ic_user

# buld and prompte the final pdf to this directory
all::
	for d in $(sub_dirs);\
	do\
		echo "build $d";\
		(cd $$d; $(MAKE) && $(MAKE) promote);\
	done

# scrub everything away execpt source
nuke::
	for d in $(sub_dirs);\
	do\
		echo "build $d";\
		(cd $$d; $(MAKE) nuke );\
	done
	rm -f ./*.pdf

# remove just tex detritis leaving final doc files
clean::
	for d in $(sub_dirs);\
	do\
		echo "build $d";\
		(cd $$d; $(MAKE) nuke );\
	done
