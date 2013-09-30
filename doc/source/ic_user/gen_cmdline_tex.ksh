#!/usr/bin/env ksh
# This really should be executed with kshell, but it should be simplistic enough for bash.
#	vi:sw=4 ts=4:

# ---------------------------------------------------------------------------------------
#
#	Mnemonic:	gen_cmdline_tex.ksh
# 	Abstract:	This script susses out the help messages from the desired .py
#				file. code and generates the bulk of the cmdline.tex file.
#				We assume that this is driven by mk or make during the build
#				document process. Input is the name of the .py file (relative path
#				under the source root) that should be parsed, the output file name,
#				and the target list name within the source to pull the data from.
#	Date:		14 Oct 2013
#	Author:		E. Scott Daniels
#
# ---------------------------------------------------------------------------------------


# we assume that the root of the source tree contains the doc directory, and that no
# directoy under doc has a doc directory. Function finds the top of the source tree
# so that we can locate the desired file.
function find_root
{
	typeset pd=$PWD

	while [[ ! -d $pd/doc ]]
	do
		if [[ $pd == ""  ]]
		then
			echo "$argv0: unable to find source root  [FAIL]"
			exit 1
		fi
		pd=${pd%/*}

	done

	echo "$pd"
}


argv0="${0##*/}"				# simple name for error messages

if [[ $1 != "/"* ]]
then
	input=$(find_root)/$1		# py soruce file we'll parse
else
	input=$1
fi
output=$2
opt_target="$3"				# string that sets off the array assignment in the source code

if [[ ! -f $input ]]
then
	echo "$argv0: cannot find input file: $input   [FAIL]"
	exit 1
fi

if [[ -z opt_target ]]
then
	echo "$argv0: missing command line parm:  option target list  [FAIL]"
	exit 1
fi

# we assume the syntax is predictable based on the cfg object and that parameters on the
# python calls are all name=value pairs with the exception of the first.
sed -r 's/^[ 	]+//' $input | awk -v squote="'" -v target=$opt_target '
	BEGIN {
		oidx = 0;
	}

	function split_first( haystack, user_target, needle,		n )
	{
		if( (n = index( haystack, needle )) > 0 )
		{
			user_target[1] = substr( haystack, 1, n-1 );
			user_target[2] = substr( haystack, n+1 );
		}
		else
		{
			user_target[1] = haystack;
			user_target[2] = "";
		}
	}

	# we assume str contains one or more key=value pairs separated with commas and with
	# potenital closing ) and ].
	function parse_rest( str, 		a, b )
	{
		while( str != "" )
		{
			if( substr( str, 1, 1 ) == "]" )
			{
				snarf = 0;						# should not be needed, but prevent accidents
				exit( 0 );						# we will only capture the first list
			}

			if( substr( str, 1, 1 ) == ")"  || substr( str, 1, 1 ) == "," || substr( str, 1, 1 ) == " " || substr( str, 1, 1 ) == "\t" )  # skip insignificant stuff
				str = substr( str, 2 );
			else
			if( ! index( str, "=" ) )			# assume bloody split string to pretend we are in the 80s and have just 24x80 crts again
			{
				split_first( str, a, "," );
				gsub( squote, "", a[1] );
				data[pname, dname] = data[pname, dname] a[1];		# join
				str = a[2];
			}
			else
			{
				split_first( str, a, "=" );
				if( substr( a[2], 1, 1 ) == squote )
					split_first( substr( a[2], 2), b, squote );
				else
				{
					if( substr( a[2], 1, 1 ) == "[" ) 		# probalby an array used as a default -- snarf the whole thing
					{
						split_first( a[2], b, "]" );
						b[1] = b[1] "]";					# add the close back that split stripped
					}
					else
						split_first( a[2], b, "," );
				}

				data_seen[a[1]] = 1;
				dname = a[1];
				data[pname, dname] = b[1];

				if( substr( b[2], 1, 1 ) == "," )
					str = substr( b[2], 2 );
				else
					str = b[2];
			}
		}
	}

	!snarf {
		snarf = match( $0, target ".*=.*[[]" ) > 0 ? 1 : 0;
		next;
	}

	/cfg\..*Opt\(/ {
		split_first( $0, a, "(" );

		split_first( a[2], b, "," );
		gsub( squote, "", b[1] );
		pname = b[1];
		order[oidx++] = pname;				# output order will match the order defined in the code
		if( b[2] != "" )
			parse_rest( b[2] );

		next;
	}

	snarf {
		parse_rest( $0 );
		next;
	}

	END {
		for( i = 0; i < oidx; i++ )
		{
			pname = order[i];

			if( data[pname, "short"] != "" )
				printf( "\\dlitemcw{-%s\n\n--%s} {\n", data[pname, "short"], pname );
			else
			{
				printf( "\\vspace{5pt}\n" );
				printf( "\\dlitemcw{--%s} {\n",  pname );
			}

			gsub( "\.$", "", data[pname, "help"] );			# on the off chance that the programmer uses proper punctuation,
			printf( "%s.\n", data[pname, "help"] );			# but seems they dont, so we assume we always need to add it.
			if( data[pname, "required"] == "True" )
				printf( "This parameter is required.\n" );
			if( data[pname, "default"] != "" && data[pname, "default"] != "None" )
				printf( "When not supplied the default used is: %s.\n", data[pname, "default"] );	# latex canNOT handle verb here :(
			printf( "}\n\n" );
		}
	}
' |sed 's/_/\\_/g' >$output


exit 0
