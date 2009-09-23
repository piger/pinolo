#!/usr/bin/env perl -w

use strict;

foreach my $line (<>) {
    next if $line =~ /^\s*$/;
    $line =~ s/\n//g;
    $line =~ s/^quote = //;
    $line =~ s/(?<!^)\<[^\>]+\>/\n$&/g;
    print "${line}\n%\n";
}
