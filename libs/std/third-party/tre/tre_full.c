/*
    Unity build file for TRE regex library.
    This allows embedding TRE directly into the generated C output
    specifically for the Zen C "regex" module.
*/

// Configuration for TRE
// Configuration for TRE
// TRE_WCHAR is defined in tre-config.h
#define TRE_MULTIBYTE 1
#define TRE_APPROX 1
#define HAVE_CONFIG_H 1

// Include implementation files
// Note: We use relative paths assuming this file is in std/third-party/tre/
// But since this is included from std/regex.zc, and eventually out.c...
//
// Actually, raw inclusions in Zen C are pasted into out.c.
// out.c is at the root.
// So we need to include them by path relative to root?
// Or we rely on the preprocessor of the backend compiler.

// If out.c contains:
// #include "std/third-party/tre/lib/regcomp.c"
// Then gcc needs to find it.

// But here we are writing a C file that includes other C files.
// Let's assume we include *this* file from out.c via regex.zc.

#include "lib/regcomp.c"
#include "lib/regerror.c"
#include "lib/regexec.c"
#include "lib/tre-ast.c"
#include "lib/tre-compile.c"
#include "lib/tre-filter.c"
#include "lib/tre-match-approx.c"
#include "lib/tre-match-backtrack.c"
#include "lib/tre-match-parallel.c"
#include "lib/tre-mem.c"
#include "lib/tre-parse.c"
#include "lib/tre-stack.c"
#include "lib/xmalloc.c"
