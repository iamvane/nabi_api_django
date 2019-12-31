# Roles
ROLE_STUDENT = 'student'
ROLE_PARENT = 'parent'
ROLE_INSTRUCTOR = 'instructor'

# --- Skill level ---
SKILL_LEVEL_BEGINNER = 'beginner'
SKILL_LEVEL_INTERMEDIATE = 'intermediate'
SKILL_LEVEL_ADVANCED = 'advanced'
SKILL_LEVEL_CHOICES = (
    (SKILL_LEVEL_BEGINNER, SKILL_LEVEL_BEGINNER),
    (SKILL_LEVEL_INTERMEDIATE, SKILL_LEVEL_INTERMEDIATE),
    (SKILL_LEVEL_ADVANCED, SKILL_LEVEL_ADVANCED),
)

# --- Day of the week ---
DAY_MONDAY = 'monday'
DAY_TUESDAY = 'tuesday'
DAY_WEDNESDAY = 'wednesday'
DAY_THURSDAY = 'thursday'
DAY_FRIDAY = 'friday'
DAY_SATURDAY = 'saturday'
DAY_SUNDAY = 'sunday'
DAY_CHOICES = (
    (DAY_SUNDAY, DAY_SUNDAY),
    (DAY_MONDAY, DAY_MONDAY),
    (DAY_TUESDAY, DAY_TUESDAY),
    (DAY_WEDNESDAY, DAY_WEDNESDAY),
    (DAY_THURSDAY, DAY_THURSDAY),
    (DAY_FRIDAY, DAY_FRIDAY),
    (DAY_SATURDAY, DAY_SATURDAY),
)
DAY_TUPLE = (DAY_MONDAY, DAY_TUESDAY, DAY_WEDNESDAY, DAY_THURSDAY, DAY_FRIDAY, DAY_SATURDAY, DAY_SUNDAY)

# --- schedule ---
SCHEDULE_8_10 = '8AM-10AM'
SCHEDULE_10_12 = '10AM-12PM'
SCHEDULE_12_3 = '12PM-3PM'
SCHEDULE_3_6 = '3PM-6PM'
SCHEDULE_CHOICES = (
    (SCHEDULE_8_10, SCHEDULE_8_10),
    (SCHEDULE_10_12, SCHEDULE_10_12),
    (SCHEDULE_12_3, SCHEDULE_12_3),
    (SCHEDULE_3_6, SCHEDULE_3_6),
)

# --- Months ---
MONTH_JANUARY = 'january'
MONTH_FEBRUARY = 'february'
MONTH_MARCH = 'march'
MONTH_APRIL = 'april'
MONTH_MAY = 'may'
MONTH_JUNE = 'june'
MONTH_JULY = 'july'
MONTH_AUGUST = 'august'
MONTH_SEPTEMBER = 'september'
MONTH_OCTOBER = 'october'
MONTH_NOVEMBER = 'november'
MONTH_DECEMBER = 'december'
MONTH_CHOICES = (
    (MONTH_JANUARY, MONTH_JANUARY),
    (MONTH_FEBRUARY, MONTH_FEBRUARY),
    (MONTH_MARCH, MONTH_MARCH),
    (MONTH_APRIL, MONTH_APRIL),
    (MONTH_MAY, MONTH_MAY),
    (MONTH_JUNE, MONTH_JUNE),
    (MONTH_JULY, MONTH_JULY),
    (MONTH_AUGUST, MONTH_AUGUST),
    (MONTH_SEPTEMBER, MONTH_SEPTEMBER),
    (MONTH_OCTOBER, MONTH_OCTOBER),
    (MONTH_NOVEMBER, MONTH_NOVEMBER),
    (MONTH_DECEMBER, MONTH_DECEMBER),
)

# --- degree types ---
DEGREE_TYPE_ASSOCIATE = 'associate'
DEGREE_TYPE_BACHELORS = 'bachelors'
DEGREE_TYPE_GRADUATE = 'graduate'
DEGREE_TYPE_PROFESSIONAL = 'professional'
DEGREE_TYPE_CERTIFICATION = 'certification'
DEGREE_TYPE_OTHER = 'other'
DEGREE_TYPE_CHOICES = (
    (DEGREE_TYPE_ASSOCIATE, 'Associate Degree'),
    (DEGREE_TYPE_BACHELORS, 'Bachelor\'s Degree'),
    (DEGREE_TYPE_GRADUATE, 'Graduate Degreee'),
    (DEGREE_TYPE_PROFESSIONAL, 'Professional Degree'),
    (DEGREE_TYPE_CERTIFICATION, 'Certification'),
    (DEGREE_TYPE_OTHER, 'Other'),
)

# --- social media ---
SOCIAL_MEDIA_INSTAGRAM = 'instagram'
SOCIAL_MEDIA_TWITTER = 'twitter'
SOCIAL_MEDIA_FACEBOOK = 'facebook'
SOCIAL_MEDIA_LINKEDIN = 'linkedin'
SOCIAL_MEDIA_CHOICES = (
    (SOCIAL_MEDIA_INSTAGRAM, SOCIAL_MEDIA_INSTAGRAM),
    (SOCIAL_MEDIA_TWITTER, SOCIAL_MEDIA_TWITTER),
    (SOCIAL_MEDIA_FACEBOOK, SOCIAL_MEDIA_FACEBOOK),
    (SOCIAL_MEDIA_LINKEDIN, SOCIAL_MEDIA_LINKEDIN),
)

# --- languages ---
LANG_ENGLISH = 'english'
LANG_SPANISH = 'spanish'
LANG_CHOICES = (
    (LANG_ENGLISH, LANG_ENGLISH),
    (LANG_SPANISH, LANG_SPANISH),
)

# --- phone types ---
PHONE_TYPE_MAIN = 'main'
PHONE_TYPE_MOBILE = 'mobile'
PHONE_TYPE_CHOICES = (
    (PHONE_TYPE_MAIN, PHONE_TYPE_MAIN),
    (PHONE_TYPE_MOBILE, PHONE_TYPE_MOBILE),
)

# --- address type ---
ADDRESS_TYPE_HOME = 'home'
ADDRESS_TYPE_BILLING = 'billing'
ADDRESS_TYPE_STUDIO = 'studio'
ADDRESS_TYPE_CHOICES = (
    (ADDRESS_TYPE_HOME, ADDRESS_TYPE_HOME),
    (ADDRESS_TYPE_BILLING, ADDRESS_TYPE_BILLING),
    (ADDRESS_TYPE_STUDIO, ADDRESS_TYPE_STUDIO),
)

# --- gender ---
GENDER_FEMALE = 'female'
GENDER_MALE = 'male'
GENDER_UNDISCLOSED = 'undisclosed'
GENDER_CHOICES = (
    (GENDER_FEMALE, GENDER_FEMALE),
    (GENDER_MALE, GENDER_MALE),
    (GENDER_UNDISCLOSED, GENDER_UNDISCLOSED),
)

# --- Places for lessons ---
PLACE_FOR_LESSONS_HOME = 'home'
PLACE_FOR_LESSONS_STUDIO = 'studio'
PLACE_FOR_LESSONS_ONLINE = 'online'
PLACE_FOR_LESSONS_CHOICES = (
    (PLACE_FOR_LESSONS_HOME, PLACE_FOR_LESSONS_HOME),
    (PLACE_FOR_LESSONS_STUDIO, PLACE_FOR_LESSONS_STUDIO),
    (PLACE_FOR_LESSONS_ONLINE, PLACE_FOR_LESSONS_ONLINE),
)

# --- lesson duration ---
LESSON_DURATION_30 = '30 mins'
LESSON_DURATION_45 = '45 mins'
LESSON_DURATION_60 = '60 mins'
LESSON_DURATION_90 = '90 mins'
LESSON_DURATION_CHOICES = (
    (LESSON_DURATION_30, LESSON_DURATION_30),
    (LESSON_DURATION_45, LESSON_DURATION_45),
    (LESSON_DURATION_60, LESSON_DURATION_60),
    (LESSON_DURATION_90, LESSON_DURATION_90),
)

# --- lesson request status ---
LR_SEEN = 'seen'
LR_NO_SEEN = 'no seen'
LR_STATUSES = (
    (LR_SEEN, LR_SEEN),
    (LR_NO_SEEN, LR_NO_SEEN),
)

# --- Job preferences ---
JOB_PREFS_ONE_STUDENT = 'one student'
JOB_PREFS_SMALL_GROUPS = 'small groups'
JOB_PREFS_LARGE_GROUPS = 'large groups'
JOB_PREFS_CHILDREN = 'children'
JOB_PREFS_TEENS = 'teens'
JOB_PREFS_ADULTS = 'adults'
JOB_PREFS_SENIORS = 'seniors'
JOB_PREFS_CHOICES = (
    (JOB_PREFS_ONE_STUDENT, JOB_PREFS_ONE_STUDENT),
    (JOB_PREFS_SMALL_GROUPS, JOB_PREFS_SMALL_GROUPS),
    (JOB_PREFS_LARGE_GROUPS, JOB_PREFS_LARGE_GROUPS),
    (JOB_PREFS_CHILDREN, JOB_PREFS_CHILDREN),
    (JOB_PREFS_TEENS, JOB_PREFS_TEENS),
    (JOB_PREFS_ADULTS, JOB_PREFS_ADULTS),
    (JOB_PREFS_SENIORS, JOB_PREFS_SENIORS),
)

# --- Qualifications ---
QUALIFICATIONS_CERT_TEACHER = 'cert. teacher'
QUALIFICATIONS_MUSIC_THERAPY = 'music therapy'
QUALIFICATIONS_MUSIC_PRODUCTION = 'music production'
QUALIFICATIONS_EAR_TRAINING = 'ear training'
QUALIFICATIONS_CONDUCTING = 'conducting'
QUALIFICATIONS_VIRTUOSO = 'virtuoso recognition'
QUALIFICATIONS_PERFORMANCE = 'performance'
QUALIFICATIONS_MUSIC_THEORY = 'music theory'
QUALIFICATIONS_YOUNG_CHILD = 'young children experience'
QUALIFICATIONS_REPERTOIRE = 'repertoire selection'
QUALIFICATIONS_CHOICES = (
    (QUALIFICATIONS_CERT_TEACHER, QUALIFICATIONS_CERT_TEACHER),
    (QUALIFICATIONS_MUSIC_THERAPY, QUALIFICATIONS_MUSIC_THERAPY),
    (QUALIFICATIONS_MUSIC_PRODUCTION, QUALIFICATIONS_MUSIC_PRODUCTION),
    (QUALIFICATIONS_EAR_TRAINING, QUALIFICATIONS_EAR_TRAINING),
    (QUALIFICATIONS_CONDUCTING, QUALIFICATIONS_CONDUCTING),
    (QUALIFICATIONS_VIRTUOSO, QUALIFICATIONS_VIRTUOSO),
    (QUALIFICATIONS_PERFORMANCE, QUALIFICATIONS_PERFORMANCE),
    (QUALIFICATIONS_MUSIC_THEORY, QUALIFICATIONS_MUSIC_THEORY),
    (QUALIFICATIONS_YOUNG_CHILD, QUALIFICATIONS_YOUNG_CHILD),
    (QUALIFICATIONS_REPERTOIRE, QUALIFICATIONS_REPERTOIRE),
)

# --- rate types ---
RATE_30 = '30 mins'
RATE_45 = '45 mins'
RATE_60 = '60 mins'
RATE_90 = '90 mins'
RATE_CHOICES = (
    (RATE_30, RATE_30),
    (RATE_45, RATE_45),
    (RATE_60, RATE_60),
    (RATE_90, RATE_90),
)

# --- student age group ---
# for search/filter
AGE_CHILD = 'children'
AGE_TEEN = 'teens'
AGE_ADULT = 'adults'
AGE_SENIOR = 'seniors'
AGE_CHOICES = (
    (AGE_CHILD, AGE_CHILD),
    (AGE_TEEN, AGE_TEEN),
    (AGE_ADULT, AGE_ADULT),
    (AGE_SENIOR, AGE_SENIOR)
)

# --- status of background check request
BG_STATUS_VERIFIED = 'VERIFIED'
BG_STATUS_PENDING = 'PENDING'
BG_STATUS_WARNING = 'WARNING'
BG_STATUS_NOT_VERIFIED = 'NOT_VERIFIED'
BG_STATUSES = (
    (BG_STATUS_NOT_VERIFIED, BG_STATUS_NOT_VERIFIED),
    (BG_STATUS_PENDING, BG_STATUS_PENDING),
    (BG_STATUS_VERIFIED, BG_STATUS_VERIFIED),
    (BG_STATUS_WARNING, BG_STATUS_WARNING)
)

# --- benefit types ---
BENEFIT_LESSON = 'lesson'
BENEFIT_TYPES = (
    (BENEFIT_LESSON, BENEFIT_LESSON),
)

# --- benefit statuses ---
BENEFIT_ENABLED = 'enable'
BENEFIT_DISABLED = 'disable'
BENEFIT_USED = 'used'
BENEFIT_STATUSES = (
    (BENEFIT_ENABLED, BENEFIT_ENABLED),
    (BENEFIT_DISABLED, BENEFIT_DISABLED),
    (BENEFIT_USED, BENEFIT_USED),
)

# --- services for payment ---
SERVICE_BG_CHECK = 'background check'
SERVICES_CHOICES = (
    (SERVICE_BG_CHECK, SERVICE_BG_CHECK),
)

# --- statuses for payment ---
PY_REGISTERED = 'registered'
PY_PROCESSED = 'processed'
PY_CANCELLED = 'cancelled'
PY_STATUSES = (
    (PY_REGISTERED, PY_REGISTERED),
    (PY_PROCESSED, PY_PROCESSED),
    (PY_CANCELLED, PY_CANCELLED),
)

HOSTNAME = "www.nabimusic.com"
HOSTNAME_PROTOCOL = "http://" + HOSTNAME
