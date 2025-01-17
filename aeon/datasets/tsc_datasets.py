"""Datasets in the UCR/tsml data archives from https://timeseriesclassification.com.

Collections of data available from timeseriesclassification.com. Data is available in
.ts format, and for some problems, in .arff and .tsv format. For any issues with these
data, please see
https://github.com/time-series-machine-learning/tsml-repo

There are four main distinctions: univariate/multivariate equal/unequal length.
Set univariate contains the 128 UCR problems, as described in [1].
Set multivariate contains the 30 UEA problems, as described in [2], plus 3 new
additions.
Set univariate_equal_length contains the 112 UCR archive problems used in [3].
Set multivariate_equal_length contains the 26 UEA archive problems used in [4].

[1] H.Dau, A. Bagnall, K. Kamgar, C. Yeh, Y. Zhu, S. Gharghabi, C. Ratanamahatana and
E. Keogh.
The  UCR  time  series  archive. IEEE/CAA J. Autom. Sinica, 6(6):1293–1305, 2019
[2] A. Bagnall, H. Dau, J. Lines, M. Flynn, J. Large, A. Bostrom, P. Southam,and
E.  Keogh.
The UEA  multivariate  time  series  classification  archive, 2018. ArXiv e-prints,
arXiv:1811.00075, 2018
[3] A. Bagnall, M. Flynn, J. Large, J. Lines and M. Middlehurst.
On the Usage and Performance of the Hierarchical Vote Collective of Transformation-Based
Ensembles Version 1.0 (HIVE-COTE v1.0). Lecture Notes in Computer Science. in proc.
5th Advanced Analytics and Learning on Temporal Data
[4] A. Pasos Ruiz, M. Flynn, J. Large, M. Middlehurst and A. Bagnall.
    The great multivariate time series classification bake off: a review and
    experimental evaluation of recent algorithmic advances,
    Data Mining and Knowledge Discovery, 2020.
[5] Middlehurst, M., Schäfer, P. & Bagnall, A.
    Bake off redux: a review and experimental evaluation of recent time series
    classification algorithms. Data Min Knowl Disc 38, 1958–2031 (2024).
    https://doi.org/10.1007/s10618-024-01022-1

"""

# The 85 UCR univariate time series classification problems in the 2015 version
univariate2015 = [
    "Adiac",
    "ArrowHead",
    "Beef",
    "BeetleFly",
    "BirdChicken",
    "Car",
    "CBF",
    "ChlorineConcentration",
    "CinCECGTorso",
    "Coffee",
    "Computers",
    "CricketX",
    "CricketY",
    "CricketZ",
    "DiatomSizeReduction",
    "DistalPhalanxOutlineCorrect",
    "DistalPhalanxOutlineAgeGroup",
    "DistalPhalanxTW",
    "Earthquakes",
    "ECG200",
    "ECG5000",
    "ECGFiveDays",
    "ElectricDevices",
    "FaceAll",
    "FaceFour",
    "FacesUCR",
    "FiftyWords",
    "Fish",
    "FordA",
    "FordB",
    "GunPoint",
    "Ham",
    "HandOutlines",
    "Haptics",
    "Herring",
    "InlineSkate",
    "InsectWingbeatSound",
    "ItalyPowerDemand",
    "LargeKitchenAppliances",
    "Lightning2",
    "Lightning7",
    "Mallat",
    "Meat",
    "MedicalImages",
    "MiddlePhalanxOutlineCorrect",
    "MiddlePhalanxOutlineAgeGroup",
    "MiddlePhalanxTW",
    "MoteStrain",
    "NonInvasiveFetalECGThorax1",
    "NonInvasiveFetalECGThorax2",
    "OliveOil",
    "OSULeaf",
    "PhalangesOutlinesCorrect",
    "Phoneme",
    "Plane",
    "ProximalPhalanxOutlineCorrect",
    "ProximalPhalanxOutlineAgeGroup",
    "ProximalPhalanxTW",
    "RefrigerationDevices",
    "ScreenType",
    "ShapeletSim",
    "ShapesAll",
    "SmallKitchenAppliances",
    "SonyAIBORobotSurface1",
    "SonyAIBORobotSurface2",
    "StarLightCurves",
    "Strawberry",
    "SwedishLeaf",
    "Symbols",
    "SyntheticControl",
    "ToeSegmentation1",
    "ToeSegmentation2",
    "Trace",
    "TwoLeadECG",
    "TwoPatterns",
    "UWaveGestureLibraryX",
    "UWaveGestureLibraryY",
    "UWaveGestureLibraryZ",
    "UWaveGestureLibraryAll",
    "Wafer",
    "Wine",
    "WordSynonyms",
    "Worms",
    "WormsTwoClass",
    "Yoga",
]


# 128 UCR univariate time series classification problems [1]
univariate = [
    "ACSF1",
    "Adiac",
    "AllGestureWiimoteX",
    "AllGestureWiimoteY",
    "AllGestureWiimoteZ",
    "ArrowHead",
    "Beef",
    "BeetleFly",
    "BirdChicken",
    "BME",
    "Car",
    "CBF",
    "Chinatown",
    "ChlorineConcentration",
    "CinCECGTorso",
    "Coffee",
    "Computers",
    "CricketX",
    "CricketY",
    "CricketZ",
    "Crop",
    "DiatomSizeReduction",
    "DistalPhalanxOutlineAgeGroup",
    "DistalPhalanxOutlineCorrect",
    "DistalPhalanxTW",
    "DodgerLoopDay",
    "DodgerLoopGame",
    "DodgerLoopWeekend",
    "Earthquakes",
    "ECG200",
    "ECG5000",
    "ECGFiveDays",
    "ElectricDevices",
    "EOGHorizontalSignal",
    "EOGVerticalSignal",
    "EthanolLevel",
    "FaceAll",
    "FaceFour",
    "FacesUCR",
    "FiftyWords",
    "Fish",
    "FordA",
    "FordB",
    "FreezerRegularTrain",
    "FreezerSmallTrain",
    "Fungi",
    "GestureMidAirD1",
    "GestureMidAirD2",
    "GestureMidAirD3",
    "GesturePebbleZ1",
    "GesturePebbleZ2",
    "GunPoint",
    "GunPointAgeSpan",
    "GunPointMaleVersusFemale",
    "GunPointOldVersusYoung",
    "Ham",
    "HandOutlines",
    "Haptics",
    "Herring",
    "HouseTwenty",
    "InlineSkate",
    "InsectEPGRegularTrain",
    "InsectEPGSmallTrain",
    "InsectWingbeatSound",
    "ItalyPowerDemand",
    "LargeKitchenAppliances",
    "Lightning2",
    "Lightning7",
    "Mallat",
    "Meat",
    "MedicalImages",
    "MelbournePedestrian",
    "MiddlePhalanxOutlineCorrect",
    "MiddlePhalanxOutlineAgeGroup",
    "MiddlePhalanxTW",
    "MixedShapesRegularTrain",
    "MixedShapesSmallTrain",
    "MoteStrain",
    "NonInvasiveFetalECGThorax1",
    "NonInvasiveFetalECGThorax2",
    "OliveOil",
    "OSULeaf",
    "PhalangesOutlinesCorrect",
    "Phoneme",
    "PickupGestureWiimoteZ",
    "PigAirwayPressure",
    "PigArtPressure",
    "PigCVP",
    "PLAID",
    "Plane",
    "PowerCons",
    "ProximalPhalanxOutlineCorrect",
    "ProximalPhalanxOutlineAgeGroup",
    "ProximalPhalanxTW",
    "RefrigerationDevices",
    "Rock",
    "ScreenType",
    "SemgHandGenderCh2",
    "SemgHandMovementCh2",
    "SemgHandSubjectCh2",
    "ShakeGestureWiimoteZ",
    "ShapeletSim",
    "ShapesAll",
    "SmallKitchenAppliances",
    "SmoothSubspace",
    "SonyAIBORobotSurface1",
    "SonyAIBORobotSurface2",
    "StarLightCurves",
    "Strawberry",
    "SwedishLeaf",
    "Symbols",
    "SyntheticControl",
    "ToeSegmentation1",
    "ToeSegmentation2",
    "Trace",
    "TwoLeadECG",
    "TwoPatterns",
    "UMD",
    "UWaveGestureLibraryAll",
    "UWaveGestureLibraryX",
    "UWaveGestureLibraryY",
    "UWaveGestureLibraryZ",
    "Wafer",
    "Wine",
    "WordSynonyms",
    "Worms",
    "WormsTwoClass",
    "Yoga",
]

# 30 UEA multivariate time series classification problems [2]
multivariate = [
    "ArticularyWordRecognition",
    "AtrialFibrillation",
    "BasicMotions",
    "CharacterTrajectories",
    "Cricket",
    "DuckDuckGeese",
    "EigenWorms",
    "Epilepsy",
    "EthanolConcentration",
    "ERing",
    "FaceDetection",
    "FingerMovements",
    "HandMovementDirection",
    "Handwriting",
    "Heartbeat",
    "InsectWingbeat",
    "JapaneseVowels",
    "Libras",
    "LSST",
    "MotorImagery",
    "NATOPS",
    "PenDigits",
    "PEMS-SF",
    "PhonemeSpectra",
    "RacketSports",
    "SelfRegulationSCP1",
    "SelfRegulationSCP2",
    "SpokenArabicDigits",
    "StandWalkJump",
    "UWaveGestureLibrary",
]

# 112 equal length/no missing univariate time series classification problems [3]
univariate_equal_length = [
    "ACSF1",
    "Adiac",
    "ArrowHead",
    "Beef",
    "BeetleFly",
    "BirdChicken",
    "BME",
    "Car",
    "CBF",
    "Chinatown",
    "ChlorineConcentration",
    "CinCECGTorso",
    "Coffee",
    "Computers",
    "CricketX",
    "CricketY",
    "CricketZ",
    "Crop",
    "DiatomSizeReduction",
    "DistalPhalanxOutlineCorrect",
    "DistalPhalanxOutlineAgeGroup",
    "DistalPhalanxTW",
    "Earthquakes",
    "ECG200",
    "ECG5000",
    "ECGFiveDays",
    "ElectricDevices",
    "EOGHorizontalSignal",
    "EOGVerticalSignal",
    "EthanolLevel",
    "FaceAll",
    "FaceFour",
    "FacesUCR",
    "FiftyWords",
    "Fish",
    "FordA",
    "FordB",
    "FreezerRegularTrain",
    "FreezerSmallTrain",
    "GunPoint",
    "GunPointAgeSpan",
    "GunPointMaleVersusFemale",
    "GunPointOldVersusYoung",
    "Ham",
    "HandOutlines",
    "Haptics",
    "Herring",
    "HouseTwenty",
    "InlineSkate",
    "InsectEPGRegularTrain",
    "InsectEPGSmallTrain",
    "InsectWingbeatSound",
    "ItalyPowerDemand",
    "LargeKitchenAppliances",
    "Lightning2",
    "Lightning7",
    "Mallat",
    "Meat",
    "MedicalImages",
    "MiddlePhalanxOutlineCorrect",
    "MiddlePhalanxOutlineAgeGroup",
    "MiddlePhalanxTW",
    "MixedShapesRegularTrain",
    "MixedShapesSmallTrain",
    "MoteStrain",
    "NonInvasiveFetalECGThorax1",
    "NonInvasiveFetalECGThorax2",
    "OliveOil",
    "OSULeaf",
    "PhalangesOutlinesCorrect",
    "Phoneme",
    "PigAirwayPressure",
    "PigArtPressure",
    "PigCVP",
    "Plane",
    "PowerCons",
    "ProximalPhalanxOutlineCorrect",
    "ProximalPhalanxOutlineAgeGroup",
    "ProximalPhalanxTW",
    "RefrigerationDevices",
    "Rock",
    "ScreenType",
    "SemgHandGenderCh2",
    "SemgHandMovementCh2",
    "SemgHandSubjectCh2",
    "ShapeletSim",
    "ShapesAll",
    "SmallKitchenAppliances",
    "SmoothSubspace",
    "SonyAIBORobotSurface1",
    "SonyAIBORobotSurface2",
    "StarLightCurves",
    "Strawberry",
    "SwedishLeaf",
    "Symbols",
    "SyntheticControl",
    "ToeSegmentation1",
    "ToeSegmentation2",
    "Trace",
    "TwoLeadECG",
    "TwoPatterns",
    "UMD",
    "UWaveGestureLibraryAll",
    "UWaveGestureLibraryX",
    "UWaveGestureLibraryY",
    "UWaveGestureLibraryZ",
    "Wafer",
    "Wine",
    "WordSynonyms",
    "Worms",
    "WormsTwoClass",
    "Yoga",
]

# 11 variable length univariate time series classification problems [3]
univariate_variable_length = [
    "AllGestureWiimoteX",
    "AllGestureWiimoteY",
    "AllGestureWiimoteZ",
    "GestureMidAirD1",
    "GestureMidAirD2",
    "GestureMidAirD3",
    "GesturePebbleZ1",
    "GesturePebbleZ2",
    "PickupGestureWiimoteZ",
    "PLAID",
    "ShakeGestureWiimoteZ",
]

# 4 fixed length univariate time series classification problems with missing values"""
univariate_missing_values = [
    "DodgerLoopDay",
    "DodgerLoopGame",
    "DodgerLoopWeekend",
    "MelbournePedestrian",
]

# 26 equal length multivariate time series classification problems [4]"""
multivariate_equal_length = [
    "ArticularyWordRecognition",
    "AtrialFibrillation",
    "BasicMotions",
    "Cricket",
    "DuckDuckGeese",
    "EigenWorms",
    "Epilepsy",
    "EthanolConcentration",
    "ERing",
    "FaceDetection",
    "FingerMovements",
    "HandMovementDirection",
    "Handwriting",
    "Heartbeat",
    "Libras",
    "LSST",
    "MotorImagery",
    "NATOPS",
    "PenDigits",
    "PEMS-SF",
    "PhonemeSpectra",
    "RacketSports",
    "SelfRegulationSCP1",
    "SelfRegulationSCP2",
    "StandWalkJump",
    "UWaveGestureLibrary",
]

# 7 variable length multivariate time series classification problems [4]"""
multivariate_unequal_length = [
    "AsphaltObstaclesCoordinates",
    "AsphaltPavementTypeCoordinates",
    "AsphaltRegularityCoordinates",
    "CharacterTrajectories",
    "InsectWingbeat",
    "JapaneseVowels",
    "SpokenArabicDigits",
]

# 158 tsml time series classification problems
tsc_zenodo = {
    "ACSF1": 11184893,
    "Adiac": 11179788,
    "AllGestureWiimoteX": 11185036,
    "AllGestureWiimoteY": 11185107,
    "AllGestureWiimoteZ": 11185136,
    "ArrowHead": 11185163,
    "Beef": 11185190,
    "BeetleFly": 11185218,
    "BirdChicken": 11185259,
    "BME": 11185291,
    "Car": 11185322,
    "CBF": 11186181,
    "Chinatown": 11186207,
    "ChlorineConcentration": 11186229,
    "CinCECGTorso": 11186247,
    "Coffee": 11186266,
    "Computers": 11186293,
    "CricketX": 11186304,
    "CricketY": 11186320,
    "CricketZ": 11186333,
    "Crop": 11186344,
    "DiatomSizeReduction": 11186365,
    "DistalPhalanxOutlineAgeGroup": 11186386,
    "DistalPhalanxOutlineCorrect": 11186597,
    "DistalPhalanxTW": 11186610,
    "DodgerLoopDay": 11186618,
    "DodgerLoopGame": 11186628,
    "DodgerLoopWeekend": 11186647,
    "Earthquakes": 11186659,
    "ECG200": 11186675,
    "ECG5000": 11186692,
    "ECGFiveDays": 11186702,
    "ElectricDevices": 11190880,
    "EOGHorizontalSignal": 11190930,
    "EOGVerticalSignal": 11190951,
    "EthanolLevel": 11190985,
    "FaceAll": 11191011,
    "FaceFour": 11191042,
    "FacesUCR": 11191065,
    "FiftyWords": 11191097,
    "Fish": 11191141,
    "FordA": 11191164,
    "FordB": 11191172,
    "FreezerRegularTrain": 11191184,
    "FreezerSmallTrain": 11191211,
    "Fungi": 11191230,
    "GestureMidAirD1": 11197478,
    "GestureMidAirD2": 11197490,
    "GestureMidAirD3": 11197504,
    "GesturePebbleZ1": 11197515,
    "GesturePebbleZ2": 11197520,
    "GunPoint": 11191244,
    "GunPointAgeSpan": 11194425,
    "GunPointMaleVersusFemale": 11194429,
    "GunPointOldVersusYoung": 11194437,
    "Ham": 11197526,
    "HandOutlines": 11197528,
    "Haptics": 11197538,
    "Herring": 11197540,
    "HouseTwenty": 11197555,
    "InlineSkate": 11197575,
    "InsectEPGRegularTrain": 11197587,
    "InsectEPGSmallTrain": 11197608,
    "InsectWingbeatSound": 11197635,
    "ItalyPowerDemand": 11197656,
    "LargeKitchenAppliances": 11197689,
    "Lightning2": 11197697,
    "Lightning7": 11197706,
    "Mallat": 11197731,
    "Meat": 11197742,
    "MedicalImages": 11197752,
    "MelbournePedestrian": 11197762,
    "MiddlePhalanxOutlineAgeGroup": 11197771,
    "MiddlePhalanxOutlineCorrect": 11197782,
    "MiddlePhalanxTW": 11197799,
    "MixedShapesRegularTrain": 11197803,
    "MixedShapesSmallTrain": 11197811,
    "MoteStrain": 11197817,
    "NonInvasiveFetalECGThorax1": 11197817,
    "NonInvasiveFetalECGThorax2": 11197831,
    "OliveOil": 11197843,
    "OSULeaf": 11197848,
    "PhalangesOutlinesCorrect": 11197875,
    "Phoneme": 11197891,
    "PickupGestureWiimoteZ": 11197898,
    "PigAirwayPressure": 11197911,
    "PigArtPressure": 11197920,
    "PigCVP": 11197924,
    "PLAID": 11197936,
    "Plane": 11197940,
    "PowerCons": 11197948,
    "ProximalPhalanxOutlineAgeGroup": 11197960,
    "ProximalPhalanxOutlineCorrect": 11197968,
    "ProximalPhalanxTW": 11197973,
    "RefrigerationDevices": 11197996,
    "Rock": 11198001,
    "ScreenType": 11198182,
    "SemgHandGenderCh2": 11198193,
    "SemgHandMovementCh2": 11198197,
    "SemgHandSubjectCh2": 11198203,
    "ShakeGestureWiimoteZ": 11198219,
    "ShapeletSim": 11198235,
    "ShapesAll": 11198237,
    "SmallKitchenAppliances": 11198251,
    "SmoothSubspace": 11198271,
    "SonyAIBORobotSurface1": 11198277,
    "SonyAIBORobotSurface2": 11198290,
    "StarLightCurves": 11198308,
    "Strawberry": 11198313,
    "SwedishLeaf": 11198315,
    "Symbols": 11198322,
    "SyntheticControl": 11198330,
    "ToeSegmentation1": 11198338,
    "ToeSegmentation2": 11198342,
    "Trace": 11198344,
    "TwoLeadECG": 11198352,
    "TwoPatterns": 11198356,
    "UMD": 11198362,
    "UWaveGestureLibraryAll": 11198366,
    "UWaveGestureLibraryX": 11198374,
    "UWaveGestureLibraryY": 11198382,
    "UWaveGestureLibraryZ": 11198384,
    "Wafer": 11198387,
    "Wine": 11198391,
    "WordSynonyms": 11198396,
    "Worms": 11198402,
    "WormsTwoClass": 11198406,
    "Yoga": 11198408,
    "ArticularyWordRecognition": 11204924,
    "AtrialFibrillation": 11206175,
    "BasicMotions": 11206179,
    "CharacterTrajectories": 11206183,
    "Cricket": 11206185,
    "DuckDuckGeese": 11206189,
    "EigenWorms": 11206196,
    "Epilepsy": 11206204,
    "EthanolConcentration": 11206212,
    "ERing": 11206210,
    "FaceDetection": 11206216,
    "FingerMovements": 11206220,
    "HandMovementDirection": 11206224,
    "Handwriting": 11206227,
    "Heartbeat": 11206229,
    "InsectWingbeat": 11206234,
    "JapaneseVowels": 11206237,
    "Libras": 11206239,
    "LSST": 11206243,
    "MotorImagery": 11206246,
    "NATOPS": 11206248,
    "PenDigits": 11206259,
    "PEMS-SF": 11206252,
    "PhonemeSpectra": 11206261,
    "RacketSports": 11206263,
    "SelfRegulationSCP1": 11206265,
    "SelfRegulationSCP2": 11206269,
    "SpokenArabicDigits": 11206274,
    "StandWalkJump": 11206278,
    "UWaveGestureLibrary": 11206282,
}

# 30 new univariate classification problems used in the bake off [5]. Some are new,
# some are discrete versions of regression problems, some are equal length versions
# of the current UCR problems and some are no missing versions of the current 128 UCR.
univariate_bake_off_2024 = [
    "AconityMINIPrinterLarge",  # AconityMINIPrinterLarge_eq
    "AconityMINIPrinterSmall",  # AconityMINIPrinterSmall_eq
    "AllGestureWiimoteX",  # AllGestureWiimoteX_eq
    "AllGestureWiimoteY",  # AllGestureWiimoteY_eq
    "AllGestureWiimoteZ",  # AllGestureWiimoteZ_eq
    "AsphaltObstacles",  # AsphaltObstaclesUni_eq
    "AsphaltPavementType",  # AsphaltPavementTypeUni_eq
    "AsphaltRegularity",  # AsphaltRegularityUni_eq
    "Colposcopy",  # Colposcopy
    "Covid3Month",  # Covid3Month_disc
    "DodgerLoopDay",  # DodgerLoopDay_nmv
    "DodgerLoopGame",  # DodgerLoopGame_nmv
    "DodgerLoopWeekend",  # DodgerLoopWeekend_nmv
    "ElectricDeviceDetection",  # ElectricDeviceDetection
    "FloodModeling1",  # FloodModeling1_disc
    "FloodModeling2",  # FloodModeling2_disc
    "FloodModeling3",  # FloodModeling3_disc
    "GestureMidAirD1",  # GestureMidAirD1_eq
    "GestureMidAirD2",  # GestureMidAirD2_eq
    "GestureMidAirD3",  # GestureMidAirD3_eq
    "GesturePebbleZ1",  # GesturePebbleZ1_eq
    "GesturePebbleZ2",  # GesturePebbleZ2_eq
    "KeplerLightCurves",  # KeplerLightCurves
    "MelbournePedestrian",  # MelbournePedestrian_nmv
    "PhoneHeartbeatSound",  # PhoneHeartbeatSound
    "PickupGestureWiimoteZ",  # PickupGestureWiimoteZ_eq
    "PLAID",  # PLAID_eq
    "ShakeGestureWiimoteZ",  # ShakeGestureWiimoteZ_eq
    "SharePriceIncrease",  # SharePriceIncrease
    "Tools",  # Tools
]
