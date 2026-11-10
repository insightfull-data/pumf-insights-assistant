* Synthetic CIUS-style PUMF. Invented data; not Statistics Canada.

DATA LIST FILE='CIUS_SYNTH_2022.txt' /
  PUMFID 1-5
  PROVINCE 6-7
  AGE_GRP 8-8
  GENDER 9-9
  HHINCQ 10-10
  EDU 11-11
  UI_010 12-12
  FQ_010 13-13
  AC_STRM 14-14
  AC_POD 15-15
  AC_MUS 16-16
  AC_NEWS 17-17
  AC_SHOP 18-18
  EC_SPND 19-19
  SM_USE 20-20
  DV_SMART 21-21
  WTPP 22-33 (4)
  WTBS_001 34-45 (4)
  WTBS_002 46-57 (4)
  WTBS_003 58-69 (4)
  WTBS_004 70-81 (4)
  WTBS_005 82-93 (4)
  WTBS_006 94-105 (4)
  WTBS_007 106-117 (4)
  WTBS_008 118-129 (4)
  WTBS_009 130-141 (4)
  WTBS_010 142-153 (4)
  WTBS_011 154-165 (4)
  WTBS_012 166-177 (4)
  WTBS_013 178-189 (4)
  WTBS_014 190-201 (4)
  WTBS_015 202-213 (4)
  WTBS_016 214-225 (4)
  WTBS_017 226-237 (4)
  WTBS_018 238-249 (4)
  WTBS_019 250-261 (4)
  WTBS_020 262-273 (4)
  WTBS_021 274-285 (4)
  WTBS_022 286-297 (4)
  WTBS_023 298-309 (4)
  WTBS_024 310-321 (4)
  WTBS_025 322-333 (4)
  WTBS_026 334-345 (4)
  WTBS_027 346-357 (4)
  WTBS_028 358-369 (4)
  WTBS_029 370-381 (4)
  WTBS_030 382-393 (4)
  WTBS_031 394-405 (4)
  WTBS_032 406-417 (4)
  WTBS_033 418-429 (4)
  WTBS_034 430-441 (4)
  WTBS_035 442-453 (4)
  WTBS_036 454-465 (4)
  WTBS_037 466-477 (4)
  WTBS_038 478-489 (4)
  WTBS_039 490-501 (4)
  WTBS_040 502-513 (4)
  WTBS_041 514-525 (4)
  WTBS_042 526-537 (4)
  WTBS_043 538-549 (4)
  WTBS_044 550-561 (4)
  WTBS_045 562-573 (4)
  WTBS_046 574-585 (4)
  WTBS_047 586-597 (4)
  WTBS_048 598-609 (4)
  WTBS_049 610-621 (4)
  WTBS_050 622-633 (4)
.

VARIABLE LABELS
  PUMFID "Public use microdata file identifier"
  PROVINCE "Province of residence"
  AGE_GRP "Age group of respondent"
  GENDER "Gender of respondent"
  HHINCQ "Household income quintile"
  EDU "Highest level of education completed"
  UI_010 "Used the Internet in the past 12 months"
  FQ_010 "Frequency of Internet use"
  AC_STRM "Watched video content online through a streaming service"
  AC_POD "Listened to podcasts"
  AC_MUS "Listened to music through a streaming service"
  AC_NEWS "Read or watched news online"
  AC_SHOP "Ordered goods or services online"
  EC_SPND "Total amount spent on online orders"
  SM_USE "Used social networking sites or apps"
  DV_SMART "Has a smartphone for personal use"
  WTPP "Final person weight"
  WTBS_001 "Bootstrap weight 1"
  WTBS_002 "Bootstrap weight 2"
  WTBS_003 "Bootstrap weight 3"
  WTBS_004 "Bootstrap weight 4"
  WTBS_005 "Bootstrap weight 5"
  WTBS_006 "Bootstrap weight 6"
  WTBS_007 "Bootstrap weight 7"
  WTBS_008 "Bootstrap weight 8"
  WTBS_009 "Bootstrap weight 9"
  WTBS_010 "Bootstrap weight 10"
  WTBS_011 "Bootstrap weight 11"
  WTBS_012 "Bootstrap weight 12"
  WTBS_013 "Bootstrap weight 13"
  WTBS_014 "Bootstrap weight 14"
  WTBS_015 "Bootstrap weight 15"
  WTBS_016 "Bootstrap weight 16"
  WTBS_017 "Bootstrap weight 17"
  WTBS_018 "Bootstrap weight 18"
  WTBS_019 "Bootstrap weight 19"
  WTBS_020 "Bootstrap weight 20"
  WTBS_021 "Bootstrap weight 21"
  WTBS_022 "Bootstrap weight 22"
  WTBS_023 "Bootstrap weight 23"
  WTBS_024 "Bootstrap weight 24"
  WTBS_025 "Bootstrap weight 25"
  WTBS_026 "Bootstrap weight 26"
  WTBS_027 "Bootstrap weight 27"
  WTBS_028 "Bootstrap weight 28"
  WTBS_029 "Bootstrap weight 29"
  WTBS_030 "Bootstrap weight 30"
  WTBS_031 "Bootstrap weight 31"
  WTBS_032 "Bootstrap weight 32"
  WTBS_033 "Bootstrap weight 33"
  WTBS_034 "Bootstrap weight 34"
  WTBS_035 "Bootstrap weight 35"
  WTBS_036 "Bootstrap weight 36"
  WTBS_037 "Bootstrap weight 37"
  WTBS_038 "Bootstrap weight 38"
  WTBS_039 "Bootstrap weight 39"
  WTBS_040 "Bootstrap weight 40"
  WTBS_041 "Bootstrap weight 41"
  WTBS_042 "Bootstrap weight 42"
  WTBS_043 "Bootstrap weight 43"
  WTBS_044 "Bootstrap weight 44"
  WTBS_045 "Bootstrap weight 45"
  WTBS_046 "Bootstrap weight 46"
  WTBS_047 "Bootstrap weight 47"
  WTBS_048 "Bootstrap weight 48"
  WTBS_049 "Bootstrap weight 49"
  WTBS_050 "Bootstrap weight 50"
.

VALUE LABELS
  PROVINCE
    10 "Newfoundland and Labrador"
    11 "Prince Edward Island"
    12 "Nova Scotia"
    13 "New Brunswick"
    24 "Quebec"
    35 "Ontario"
    46 "Manitoba"
    47 "Saskatchewan"
    48 "Alberta"
    59 "British Columbia"
  /AGE_GRP
    1 "15 to 24 years"
    2 "25 to 34 years"
    3 "35 to 44 years"
    4 "45 to 54 years"
    5 "55 to 64 years"
    6 "65 years and over"
  /GENDER
    1 "Men+"
    2 "Women+"
  /HHINCQ
    1 "Lowest quintile"
    2 "Second quintile"
    3 "Third quintile"
    4 "Fourth quintile"
    5 "Highest quintile"
    9 "Not stated"
  /EDU
    1 "High school or less"
    2 "College, CEGEP or trades"
    3 "University degree"
    9 "Not stated"
  /UI_010
    1 "Yes"
    2 "No"
    9 "Not stated"
  /FQ_010
    1 "Several times a day"
    2 "About once a day"
    3 "At least once a week"
    4 "Less than once a week"
    6 "Valid skip"
    7 "Don't know"
    8 "Refusal"
    9 "Not stated"
  /AC_STRM
    1 "Yes"
    2 "No"
    6 "Valid skip"
    7 "Don't know"
    8 "Refusal"
    9 "Not stated"
  /AC_POD
    1 "Yes"
    2 "No"
    6 "Valid skip"
    7 "Don't know"
    8 "Refusal"
    9 "Not stated"
  /AC_MUS
    1 "Yes"
    2 "No"
    6 "Valid skip"
    7 "Don't know"
    8 "Refusal"
    9 "Not stated"
  /AC_NEWS
    1 "Yes"
    2 "No"
    6 "Valid skip"
    7 "Don't know"
    8 "Refusal"
    9 "Not stated"
  /AC_SHOP
    1 "Yes"
    2 "No"
    6 "Valid skip"
    7 "Don't know"
    8 "Refusal"
    9 "Not stated"
  /SM_USE
    1 "Yes"
    2 "No"
    6 "Valid skip"
    7 "Don't know"
    8 "Refusal"
    9 "Not stated"
  /EC_SPND
    1 "Less than $100"
    2 "$100 to $499"
    3 "$500 to $999"
    4 "$1,000 or more"
    6 "Valid skip"
    7 "Don't know"
    8 "Refusal"
    9 "Not stated"
  /DV_SMART
    1 "Yes"
    2 "No"
    9 "Not stated"
.

MISSING VALUES HHINCQ (9).
MISSING VALUES EDU (9).
MISSING VALUES UI_010 (9).
MISSING VALUES DV_SMART (9).
MISSING VALUES FQ_010 (6 THRU 9).
MISSING VALUES AC_STRM (6 THRU 9).
MISSING VALUES AC_POD (6 THRU 9).
MISSING VALUES AC_MUS (6 THRU 9).
MISSING VALUES AC_NEWS (6 THRU 9).
MISSING VALUES AC_SHOP (6 THRU 9).
MISSING VALUES SM_USE (6 THRU 9).
MISSING VALUES EC_SPND (6 THRU 9).

EXECUTE.
