/**
 * appearance.js  v3 — Key-Based Auto-Translation
 * ─────────────────────────────────────────────────────────────
 * Drop in:  /static/js/appearance.js
 * Include on every user page inside <head>:
 *   <script src="/static/js/appearance.js"></script>
 *
 * HOW TRANSLATION WORKS:
 *   1. LANG['english'] defines the canonical English text for each key.
 *   2. On page load the engine builds a reverse map:
 *        english text  →  { filipino: '...', hiligaynon: '...' }
 *   3. It then walks every visible DOM text node and attribute,
 *      replacing English strings with the chosen language.
 *   4. NO data-lang-key attributes needed on any HTML file.
 *
 * TO ADD A NEW PHRASE: add the same key to all three language
 * objects in LANG. That's it — every page picks it up.
 * ─────────────────────────────────────────────────────────────
 */

(function () {

  /* ═══════════════════════════════════════════════════════════
     THEME DEFINITIONS
  ═══════════════════════════════════════════════════════════ */
  const THEMES = {
    ocean:    { '--bg1':'#1e2d3d', '--bg2':'#2f3f4d', '--bg3':'#42586b',  '--accent':'#9fc1e1', '--accent2':'#48c78e' },
    midnight: { '--bg1':'#1a1a2e', '--bg2':'#2a1a3e', '--bg3':'#4a1942',  '--accent':'#c39bd3', '--accent2':'#48c78e' },
    forest:   { '--bg1':'#1a2f1a', '--bg2':'#243d24', '--bg3':'#2d5a27',  '--accent':'#82c991', '--accent2':'#48c78e' },
    amber:    { '--bg1':'#2a1a0e', '--bg2':'#3d2a10', '--bg3':'#5a3a1a',  '--accent':'#f0b050', '--accent2':'#f5c842' },
    cobalt:   { '--bg1':'#0d1b2e', '--bg2':'#1a2a4a', '--bg3':'#1a3a5a',  '--accent':'#5ba8e0', '--accent2':'#48c78e' },
    slate:    { '--bg1':'#1a1a1a', '--bg2':'#2d2d2d', '--bg3':'#3d3d3d',  '--accent':'#a0aec0', '--accent2':'#68d391' },
  };

  /* ═══════════════════════════════════════════════════════════
     LANGUAGE PACK
  ═══════════════════════════════════════════════════════════ */
  const LANG = {
    english: {
      // ── Navigation ────────────────────────────────────────
      'nav.home':                   'Home',
      'nav.browse':                 'Browse Books',
      'nav.favorites':              'My Favorites',
      'nav.notifications':          'Notifications',
      'nav.settings':               'Settings',
      'nav.logout':                 'Sign Out',
      'nav.logout.alt':             'Logout',
      'nav.about':                  'About Us',
      'nav.features':               'Features',
      'nav.vision':                 'Vision & Mission',
      'nav.borrow':                 'Borrow',
      'nav.borrowed':               'Borrowed Books',
      'nav.duedate':                'Due Date',
      'nav.editprofile':            'Edit Profile',
      'nav.borrowhistory':          'Borrow History',

      // ── Home / Hero ───────────────────────────────────────
      'hero.welcome':               'Welcome to the',
      'hero.tagline':               'Heart of Knowledge',
      'greeting':                   'Welcome back',
      'hero.explore':               'Explore Books',
      'hero.features':              'Our Features',
      'hero.offer':                 'What We Offer',
      'hero.offer.sub':             'Everything you need — all in one place.',
      'hero.desc':                  'your gateway to books, heritage, and lifelong learning.',

      // ── Feature cards ─────────────────────────────────────
      'feat.catalog':               'Book Catalog & Search',
      'feat.catalog.desc':          'Browse thousands of titles across all categories — from Philippine literature to science, technology, and more.',
      'feat.catalog.link':          'Browse Catalog',
      'feat.borrow':                'Book Borrowing',
      'feat.borrow.desc':           'Check out books for home reading. Track your borrowed titles and due dates from your member profile.',
      'feat.borrow.link':           'Borrow a Book',
      'feat.digital':               'Digital Resources',
      'feat.digital.desc':          'Access e-books, online databases, and digital periodicals available to all registered members 24/7.',
      'feat.digital.link':          'Go Digital',
      'feat.archive':               'Local History Archive',
      'feat.archive.desc':          "Explore Iloilo's rich heritage through curated documents, photographs, and rare historical texts.",
      'feat.archive.link':          'Explore Archive',
      'feat.rooms':                 'Reading Rooms',
      'feat.rooms.desc':            'Quiet, comfortable reading spaces for individuals and groups — ideal for students and researchers alike.',
      'feat.rooms.link':            'Reserve a Seat',
      'feat.events':                'Events & Programs',
      'feat.events.desc':           'Join storytelling sessions, author talks, literacy workshops, and community events throughout the year.',
      'feat.events.link':           'See Schedule',

      // ── Vision & Mission ──────────────────────────────────
      'vm.title':                   'Our Vision & Mission',
      'vm.sub':                     'The values that guide everything we do.',
      'vm.vision':                  'Vision',
      'vm.vision.desc':             'To be a welcoming and inclusive public library that empowers the community through access to knowledge, lifelong learning, and cultural enrichment.',
      'vm.mission':                 'Mission',
      'vm.mission.desc':            'To provide accessible information resources, promote literacy and education, and support learning, research, and personal growth for all members of the community.',
      'vm.values':                  'Core Values',
      'vm.values.desc':             'Accessibility, Integrity, Service, and Community — fostering a culture of learning and responsible information sharing.',

      // ── Browse page ───────────────────────────────────────
      'books.title':                'Browse Books',
      'books.sub':                  'Discover your next great read from our collection',
      'books.categories':           'All Categories',
      'books.details':              'Details',
      'books.modal.title':          'Book Details',
      'books.borrow':               'Borrow This Book',
      'books.close':                'Close',
      'books.loading':              'Loading…',
      'books.empty':                'No books found matching your search.',
      'books.fav.full':             'Favorites Full!',
      'books.fav.full.desc':        'Remove a favorite first before adding a new one.',
      'books.badge.new':            'New',
      'books.badge.empty':          'Empty',

      // ── Edit Profile ──────────────────────────────────────
      'profile.title':              'Edit Profile',
      'profile.sub':                'Keep your information up to date',
      'profile.account':            'Account',
      'profile.personal':           'Personal Information',
      'profile.contact':            'Contact',
      'profile.firstname':          'First Name',
      'profile.lastname':           'Last Name',
      'profile.age':                'Age',
      'profile.sex':                'Sex',
      'profile.phone':              'Phone Number',
      'profile.address':            'Address',
      'profile.email':              'Username / Email',
      'profile.save':               'Save Changes',
      'profile.cancel':             'Cancel',
      'profile.male':               'Male',
      'profile.female':             'Female',

      // ── Settings ──────────────────────────────────────────
      'settings.overview':          'Overview',
      'settings.personal':          'Personal Details',
      'settings.password':          'Password & Security',
      'settings.appearance':        'Appearance',
      'settings.privacy':           'Privacy',
      'settings.data':              'Data & Storage',
      'settings.danger':            'Danger Zone',
      'settings.pw.update':         'Update Password',
      'settings.pw.current':        'Current Password',
      'settings.pw.new':            'New Password',
      'settings.pw.confirm':        'Confirm Password',
      'settings.since':             'Member Since',
      'settings.borrowed':          'Books Borrowed',
      'settings.theme':             'Color Theme',
      'settings.language':          'Language',
      'settings.lang.label':        'Interface Language',
      'settings.clear':             'Clear',
      'settings.delete':            'Delete Account',
      'settings.saved':             'Changes saved',

      // ── About Us ──────────────────────────────────────────
      'about.eyebrow':              'About the Library',
      'about.title':                'About Us',
      'about.who':                  'Who We Are',
      'about.who.sub':              'Our story, our purpose.',
      'about.history':              'Our History',
      'about.history.sub':          'Key milestones in our journey.',
      'about.services':             'Our Services',
      'about.services.sub':         'Everything we offer to serve the community.',
      'about.map':                  'Find Us',
      'about.map.sub':              "We're right here in the heart of Iloilo City.",
      'about.svc.lending':          'Book Lending',
      'about.svc.digital':          'Digital Resources',
      'about.svc.research':         'Research Assistance',
      'about.svc.museum':           'Museum Exhibits',
      'about.svc.community':        'Community Programs',
      'about.svc.study':            'Study Spaces',
      'about.addr':                 'Address',
      'about.hours':                'Library Hours',
      'about.contact':              'Contact Information',

      // ── Common UI ─────────────────────────────────────────
      'ui.member':                  'Member',
      'ui.email':                   'Email',
      'ui.phone':                   'Phone',
      'ui.search':                  'Search',
      'ui.save':                    'Save',
      'ui.edit':                    'Edit',
      'ui.delete':                  'Delete',
      'ui.confirm':                 'Confirm',
      'ui.cancel':                  'Cancel',
      'ui.close':                   'Close',
      'ui.loading':                 'Loading',
      'ui.noresults':               'No results found',
      'ui.markread':                'Mark all as read',
      'ui.unread':                  'unread',
      'ui.noannounce':              'No announcements yet',
      'ui.justnow':                 'Just now',
      'ui.contact':                 'Contact',
      'ui.personal':                'Personal Details',

      // ── Placeholders ──────────────────────────────────────
      'ph.search':                  'Search books…',
      'ph.search.full':             'Search by title, author, or ISBN…',
    },

    /* ─────────────────────────────────────────────────────────
       FILIPINO
    ───────────────────────────────────────────────────────── */
    filipino: {
      'nav.home':                   'Tahanan',
      'nav.browse':                 'Mag-browse ng Libro',
      'nav.favorites':              'Mga Paboritong Libro',
      'nav.notifications':          'Mga Abiso',
      'nav.settings':               'Mga Setting',
      'nav.logout':                 'Mag-sign Out',
      'nav.logout.alt':             'Mag-sign Out',
      'nav.about':                  'Tungkol sa Amin',
      'nav.features':               'Mga Tampok',
      'nav.vision':                 'Bisyon at Misyon',
      'nav.borrow':                 'Humiram',
      'nav.borrowed':               'Mga Hiram na Libro',
      'nav.duedate':                'Takdang Petsa',
      'nav.editprofile':            'I-edit ang Profile',
      'nav.borrowhistory':          'Kasaysayan ng Hiraman',

      'hero.welcome':               'Maligayang pagdating sa',
      'hero.tagline':               'Sentro ng Kaalaman',
      'greeting':                   'Maligayang pagbabalik',
      'hero.explore':               'I-explore ang Libro',
      'hero.features':              'Aming mga Tampok',
      'hero.offer':                 'Aming Inaalok',
      'hero.offer.sub':             'Lahat ng kailangan mo — nasa iisang lugar.',
      'hero.desc':                  'ang iyong daan patungo sa mga libro, pamana, at panghabambuhay na pag-aaral.',

      'feat.catalog':               'Katalogo at Paghahanap ng Libro',
      'feat.catalog.desc':          'Mag-browse ng libu-libong pamagat sa iba\'t ibang kategorya — mula sa panitikang Pilipino hanggang agham, teknolohiya, at marami pa.',
      'feat.catalog.link':          'I-browse ang Katalogo',
      'feat.borrow':                'Pagpapahiram ng Libro',
      'feat.borrow.desc':           'Humiram ng mga libro para basahin sa bahay. Subaybayan ang iyong mga hiram na libro at takdang petsa mula sa iyong profile.',
      'feat.borrow.link':           'Humiram ng Libro',
      'feat.digital':               'Mga Digital na Mapagkukunan',
      'feat.digital.desc':          'I-access ang mga e-book, online database, at digital na periodical na available sa lahat ng miyembro 24/7.',
      'feat.digital.link':          'Pumunta sa Digital',
      'feat.archive':               'Arkibo ng Lokal na Kasaysayan',
      'feat.archive.desc':          'Tuklasin ang mayamang pamana ng Iloilo sa pamamagitan ng mga curated na dokumento, larawan, at bihirang makasaysayang teksto.',
      'feat.archive.link':          'I-explore ang Arkibo',
      'feat.rooms':                 'Mga Silid-Basa',
      'feat.rooms.desc':            'Tahimik at komportableng lugar para sa indibidwal at grupo — perpekto para sa mga estudyante at mananaliksik.',
      'feat.rooms.link':            'Mag-reserba ng Upuan',
      'feat.events':                'Mga Kaganapan at Programa',
      'feat.events.desc':           'Sumali sa mga sesyon ng pagkukuwento, talumpati ng may-akda, workshop sa literacy, at mga aktibidad sa komunidad.',
      'feat.events.link':           'Tingnan ang Iskedyul',

      'vm.title':                   'Aming Bisyon at Misyon',
      'vm.sub':                     'Ang mga pagpapahalaga na gumagabay sa lahat ng aming ginagawa.',
      'vm.vision':                  'Bisyon',
      'vm.vision.desc':             'Maging isang bukas at inklusibong pampublikong aklatan na nagbibigay-kapangyarihan sa komunidad sa pamamagitan ng kaalaman, panghabambuhay na pag-aaral, at pagpapayaman ng kultura.',
      'vm.mission':                 'Misyon',
      'vm.mission.desc':            'Magbigay ng accessible na mapagkukunan ng impormasyon, itaguyod ang literacy at edukasyon, at suportahan ang pag-aaral, pananaliksik, at personal na paglago para sa lahat.',
      'vm.values':                  'Mga Pangunahing Pagpapahalaga',
      'vm.values.desc':             'Accessibility, Integridad, Serbisyo, at Komunidad — nagtataguyod ng kultura ng pag-aaral at responsableng pagbabahagi ng impormasyon.',

      'books.title':                'Mag-browse ng Libro',
      'books.sub':                  'Tuklasin ang iyong susunod na magandang babasahin mula sa aming koleksyon',
      'books.categories':           'Lahat ng Kategorya',
      'books.details':              'Detalye',
      'books.modal.title':          'Detalye ng Libro',
      'books.borrow':               'Hiramin ang Librong Ito',
      'books.close':                'Isara',
      'books.loading':              'Naglo-load…',
      'books.empty':                'Walang libro na nahanap.',
      'books.fav.full':             'Puno na ang Paborito!',
      'books.fav.full.desc':        'Alisin muna ang isang paborito bago magdagdag ng bago.',
      'books.badge.new':            'Bago',
      'books.badge.empty':          'Walang laman',

      'profile.title':              'I-edit ang Profile',
      'profile.sub':                'Panatilihing updated ang iyong impormasyon',
      'profile.account':            'Account',
      'profile.personal':           'Personal na Impormasyon',
      'profile.contact':            'Makipag-ugnayan',
      'profile.firstname':          'Unang Pangalan',
      'profile.lastname':           'Apelyido',
      'profile.age':                'Edad',
      'profile.sex':                'Kasarian',
      'profile.phone':              'Numero ng Telepono',
      'profile.address':            'Tirahan',
      'profile.email':              'Username / Email',
      'profile.save':               'I-save ang Pagbabago',
      'profile.cancel':             'Ikansela',
      'profile.male':               'Lalaki',
      'profile.female':             'Babae',

      'settings.overview':          'Pangkalahatang-tanaw',
      'settings.personal':          'Personal na Detalye',
      'settings.password':          'Password at Seguridad',
      'settings.appearance':        'Hitsura',
      'settings.privacy':           'Privacy',
      'settings.data':              'Data at Imbakan',
      'settings.danger':            'Mapanganib na Lugar',
      'settings.pw.update':         'I-update ang Password',
      'settings.pw.current':        'Kasalukuyang Password',
      'settings.pw.new':            'Bagong Password',
      'settings.pw.confirm':        'Kumpirmahin ang Password',
      'settings.since':             'Miyembro Mula',
      'settings.borrowed':          'Mga Librong Hiram',
      'settings.theme':             'Kulay ng Tema',
      'settings.language':          'Wika',
      'settings.lang.label':        'Wika ng Interface',
      'settings.clear':             'Linisin',
      'settings.delete':            'Burahin ang Account',
      'settings.saved':             'Nai-save ang pagbabago',

      'about.eyebrow':              'Tungkol sa Aklatan',
      'about.title':                'Tungkol sa Amin',
      'about.who':                  'Sino Kami',
      'about.who.sub':              'Ang aming kwento, ang aming layunin.',
      'about.history':              'Aming Kasaysayan',
      'about.history.sub':          'Mga pangunahing tagumpay sa aming paglalakbay.',
      'about.services':             'Aming Mga Serbisyo',
      'about.services.sub':         'Lahat ng aming inaalok para sa komunidad.',
      'about.map':                  'Hanapin Kami',
      'about.map.sub':              'Nandito kami sa gitna ng Iloilo City.',
      'about.svc.lending':          'Pagpapahiram ng Libro',
      'about.svc.digital':          'Mga Digital na Mapagkukunan',
      'about.svc.research':         'Tulong sa Pananaliksik',
      'about.svc.museum':           'Mga Eksibisyon sa Museo',
      'about.svc.community':        'Mga Programang Pang-komunidad',
      'about.svc.study':            'Lugar para sa Pag-aaral',
      'about.addr':                 'Tirahan',
      'about.hours':                'Oras ng Aklatan',
      'about.contact':              'Impormasyon sa Pakikipag-ugnayan',

      'ui.member':                  'Miyembro',
      'ui.email':                   'Email',
      'ui.phone':                   'Telepono',
      'ui.search':                  'Maghanap',
      'ui.save':                    'I-save',
      'ui.edit':                    'I-edit',
      'ui.delete':                  'Burahin',
      'ui.confirm':                 'Kumpirmahin',
      'ui.cancel':                  'Ikansela',
      'ui.close':                   'Isara',
      'ui.loading':                 'Naglo-load',
      'ui.noresults':               'Walang nahanap',
      'ui.markread':                'Markahan lahat bilang nabasa',
      'ui.unread':                  'hindi nabasa',
      'ui.noannounce':              'Wala pang anunsyo',
      'ui.justnow':                 'Kararating lang',
      'ui.contact':                 'Makipag-ugnayan',
      'ui.personal':                'Personal na Detalye',

      'ph.search':                  'Maghanap ng libro…',
      'ph.search.full':             'Maghanap ayon sa pamagat, may-akda, o ISBN…',
    },

    /* ─────────────────────────────────────────────────────────
       HILIGAYNON
    ───────────────────────────────────────────────────────── */
    hiligaynon: {
      'nav.home':                   'Balay',
      'nav.browse':                 'Pangita sang Libro',
      'nav.favorites':              'Mga Paborito nga Libro',
      'nav.notifications':          'Mga Pahibalo',
      'nav.settings':               'Mga Setting',
      'nav.logout':                 'Mag-log out',
      'nav.logout.alt':             'Mag-log out',
      'nav.about':                  'Parte sa Amon',
      'nav.features':               'Mga Bahin',
      'nav.vision':                 'Bisyon kag Misyon',
      'nav.borrow':                 'Hulam',
      'nav.borrowed':               'Mga Nahulam nga Libro',
      'nav.duedate':                'Petsa sang Pagbalik',
      'nav.editprofile':            'I-edit ang Profile',
      'nav.borrowhistory':          'Kasaysayan sang Pagpanghulam',

      'hero.welcome':               'Maayong pag-abot sa',
      'hero.tagline':               'Sentro sang Kaalam',
      'greeting':                   'Maayong pagbalik',
      'hero.explore':               'Tukibon ang Libro',
      'hero.features':              'Amon mga Bahin',
      'hero.offer':                 'Amon Ginahatag',
      'hero.offer.sub':             'Tanan nga imo kinahanglan — ara diri sa isa ka lugar.',
      'hero.desc':                  'Ang imo dalan pakadto sa mga libro, kultura, kag padayon nga pagtuon.',

      'feat.catalog':               'Katalogo kag Pagpangita sang Libro',
      'feat.catalog.desc':          'Magpangita sang madamo nga titulo sa nagkalain-lain nga kategorya — halin sa panitikang Pilipino tubtob sa agham kag teknolohiya.',
      'feat.catalog.link':          'Tan-awa ang Katalogo',
      'feat.borrow':                'Pagpanghulam sang Libro',
      'feat.borrow.desc':           'Pwede ka makahulam sang libro para basahon sa balay kag bantayan ang petsa sang pagbalik.',
      'feat.borrow.link':           'Hulam sang Libro',
      'feat.digital':               'Mga Digital nga Rekurso',
      'feat.digital.desc':          'Ma-access ang e-book, online database, kag iban pa nga digital nga materyales bisan san-o.',
      'feat.digital.link':          'Tan-awa ang Digital',
      'feat.archive':               'Arkibo sang Lokal nga Kasaysayan',
      'feat.archive.desc':          'Diskubreha ang kasaysayan sang Iloilo paagi sa mga dokumento kag litrato.',
      'feat.archive.link':          'Tukibon ang Arkibo',
      'feat.rooms':                 'Mga Kwarto sang Pagbasa',
      'feat.rooms.desc':            'Hilum kag komportable nga lugar para sa pagtuon.',
      'feat.rooms.link':            'Magpareserba sang Lingkoranan',
      'feat.events':                'Mga Hitabo kag Programa',
      'feat.events.desc':           'Mag-upod sa mga workshop, aktibidad, kag programa sang komunidad.',
      'feat.events.link':           'Tan-awa ang Iskedyul',

      'vm.title':                   'Amon Bisyon kag Misyon',
      'vm.sub':                     'Mga ginahalinan sang amon ginahimo.',
      'vm.vision':                  'Bisyon',
      'vm.vision.desc':             'Mangin bukas kag inklusibo nga librarya nga nagahatag kaalam sa komunidad.',
      'vm.mission':                 'Misyon',
      'vm.mission.desc':            'Maghatag sang accessible nga impormasyon kag mag-suporta sa pagtuon.',
      'vm.values':                  'Mga Hiyas',
      'vm.values.desc':             'Integridad, Serbisyo, kag Komunidad.',

      'books.title':                'Pangita sang Libro',
      'books.sub':                  'Pilia ang imo sunod nga basahon',
      'books.categories':           'Tanan nga Kategorya',
      'books.details':              'Detalye',
      'books.modal.title':          'Detalye sang Libro',
      'books.borrow':               'Hulamon ini nga Libro',
      'books.close':                'Isara',
      'books.loading':              'Nagaload…',
      'books.empty':                'Wala sing libro nga nakita.',
      'books.fav.full':             'Puno na ang Paborito!',
      'books.fav.full.desc':        'Kuhaa anay ang isa antes magdugang bag-o.',
      'books.badge.new':            'Bag-o',
      'books.badge.empty':          'Wala',

      'profile.title':              'I-edit ang Profile',
      'profile.sub':                'Siguraduhon nga sakto ang imo impormasyon',
      'profile.account':            'Account',
      'profile.personal':           'Personal nga Detalye',
      'profile.contact':            'Kontak',
      'profile.firstname':          'Ngalan',
      'profile.lastname':           'Apelyido',
      'profile.age':                'Edad',
      'profile.sex':                'Sekso',
      'profile.phone':              'Numero sang Telepono',
      'profile.address':            'Adres',
      'profile.email':              'Email',
      'profile.save':               'I-save',
      'profile.cancel':             'Kanselahon',
      'profile.male':               'Lalaki',
      'profile.female':             'Babayi',

      'settings.overview':          'Pangkabilugan nga Talan-awon',
      'settings.personal':          'Personal nga Detalye',
      'settings.password':          'Password kag Seguridad',
      'settings.appearance':        'Hitsura',
      'settings.privacy':           'Pribasiya',
      'settings.data':              'Data kag Imbakan',
      'settings.danger':            'Delikado nga Parte',
      'settings.pw.update':         'Bag-uhon ang Password',
      'settings.pw.current':        'Karon nga Password',
      'settings.pw.new':            'Bag-o nga Password',
      'settings.pw.confirm':        'Kumpirmahon ang Password',
      'settings.since':             'Miyembro halin pa',
      'settings.borrowed':          'Nahulam nga Libro',
      'settings.theme':             'Tema',
      'settings.language':          'Pulong',
      'settings.lang.label':        'Pulong sang Interface',
      'settings.clear':             'Limpyoha',
      'settings.delete':            'Puraon ang Account',
      'settings.saved':             'Naka-save na',

      'about.eyebrow':              'Parte sa Librarya',
      'about.title':                'Parte sa Amon',
      'about.who':                  'Sin-o Kami',
      'about.who.sub':              'Ang amon estorya kag katuyuan.',
      'about.history':              'Amon Kasaysayan',
      'about.history.sub':          'Mga importante nga hitabo sa amon pagbiyahe.',
      'about.services':             'Amon mga Serbisyo',
      'about.services.sub':         'Mga ginahatag namon sa komunidad.',
      'about.map':                  'Pangitaa Kami',
      'about.map.sub':              'Makita kami sa Iloilo City.',
      'about.svc.lending':          'Pagpanghulam sang Libro',
      'about.svc.digital':          'Digital nga Rekurso',
      'about.svc.research':         'Bulig sa Panaliksik',
      'about.svc.museum':           'Eksibit sang Museo',
      'about.svc.community':        'Programa sang Komunidad',
      'about.svc.study':            'Lugar sang Pagtuon',
      'about.addr':                 'Adres',
      'about.hours':                'Oras sang Librarya',
      'about.contact':              'Kontak',

      'ui.member':                  'Miyembro',
      'ui.email':                   'Email',
      'ui.phone':                   'Telepono',
      'ui.search':                  'Pangita',
      'ui.save':                    'I-save',
      'ui.edit':                    'I-edit',
      'ui.delete':                  'Puraon',
      'ui.confirm':                 'Kumpirmahon',
      'ui.cancel':                  'Kanselahon',
      'ui.close':                   'Isara',
      'ui.loading':                 'Nagaload',
      'ui.noresults':               'Wala sing nakita',
      'ui.markread':                'Markahan tanan nga nabasa',
      'ui.unread':                  'Wala pa nabasa',
      'ui.noannounce':              'Wala pa sing anunsyo',
      'ui.justnow':                 'Bag-o lang',
      'ui.contact':                 'Kontak',
      'ui.personal':                'Personal nga Detalye',

      'ph.search':                  'Pangitaa ang libro…',
      'ph.search.full':             'Pangitaa paagi sa titulo, manunulat, ukon ISBN…',
    },
  };

  /* ═══════════════════════════════════════════════════════════
     REVERSE LOOKUP ENGINE
  ═══════════════════════════════════════════════════════════ */
  function buildLookup() {
    const lookup  = {};
    const english = LANG.english;
    const others  = Object.keys(LANG).filter(l => l !== 'english');

    for (const key of Object.keys(english)) {
      const srcText = english[key];
      if (!srcText) continue;
      lookup[srcText] = {};
      for (const lang of others) {
        if (LANG[lang][key]) lookup[srcText][lang] = LANG[lang][key];
      }
    }
    return lookup;
  }

  let LOOKUP  = buildLookup();
  let PHRASES = Object.keys(LOOKUP).sort((a, b) => b.length - a.length);

  /* ─────────────────────────────────────────────────────────
     Translate a single string
  ───────────────────────────────────────────────────────── */
  function translateText(text, lang) {
    if (!text || !text.trim() || lang === 'english') return null;
    let out = text;
    for (const phrase of PHRASES) {
      if (!out.includes(phrase)) continue;
      const tr = LOOKUP[phrase]?.[lang];
      if (tr) out = out.split(phrase).join(tr);
    }
    return out === text ? null : out;
  }

  const SKIP_TAGS = new Set([
    'SCRIPT','STYLE','NOSCRIPT','CODE','PRE',
    'TEXTAREA','SVG','CANVAS','IFRAME',
  ]);

  /* ─────────────────────────────────────────────────────────
     Original text store
  ───────────────────────────────────────────────────────── */
  const ORIG_NODES = new Map();
  const ORIG_PH    = new Map();

  function collectNodes() {
    if (!document.body) return [];
    const walker = document.createTreeWalker(
      document.body,
      NodeFilter.SHOW_TEXT,
      {
        acceptNode(node) {
          let p = node.parentElement;
          while (p) {
            if (SKIP_TAGS.has(p.tagName)) return NodeFilter.FILTER_REJECT;
            p = p.parentElement;
          }
          return node.textContent.trim()
            ? NodeFilter.FILTER_ACCEPT
            : NodeFilter.FILTER_REJECT;
        }
      }
    );
    const nodes = [];
    while (walker.nextNode()) nodes.push(walker.currentNode);
    return nodes;
  }

  function snapshotOriginals() {
    collectNodes().forEach(node => {
      if (!ORIG_NODES.has(node)) ORIG_NODES.set(node, node.textContent);
    });
    document.querySelectorAll('[placeholder]').forEach(el => {
      if (!ORIG_PH.has(el)) ORIG_PH.set(el, el.getAttribute('placeholder') || '');
    });
  }

  /* ─────────────────────────────────────────────────────────
     Walk the DOM and translate / restore
  ───────────────────────────────────────────────────────── */
  function walkAndTranslate(lang) {
    if (!document.body) return;

    snapshotOriginals();

    ORIG_NODES.forEach((orig, node) => {
      if (!node.isConnected) { ORIG_NODES.delete(node); return; }
      if (lang === 'english') {
        node.textContent = orig;
      } else {
        const tr = translateText(orig, lang);
        node.textContent = tr !== null ? tr : orig;
      }
    });

    ORIG_PH.forEach((orig, el) => {
      if (!el.isConnected) { ORIG_PH.delete(el); return; }
      if (lang === 'english') {
        el.setAttribute('placeholder', orig);
      } else {
        const tr = translateText(orig, lang);
        el.setAttribute('placeholder', tr !== null ? tr : orig);
      }
    });

    document.documentElement.lang =
      lang === 'filipino' ? 'fil' : lang === 'hiligaynon' ? 'hil' : 'en';
    document.documentElement.dataset.language = lang;
  }

  /* ═══════════════════════════════════════════════════════════
     THEME / LANGUAGE  — public apply functions
  ═══════════════════════════════════════════════════════════ */
  function applyTheme(theme) {
    const vars = THEMES[theme] || THEMES.ocean;
    Object.entries(vars).forEach(([k, v]) =>
      document.documentElement.style.setProperty(k, v));
    document.documentElement.dataset.theme = theme;
  }

  function applyLanguage(lang) {
    if (document.readyState === 'loading') {
      document.addEventListener('DOMContentLoaded', () => {
        snapshotOriginals();
        walkAndTranslate(lang);
      }, { once: true });
    } else {
      snapshotOriginals();
      walkAndTranslate(lang);
    }
  }

  /* ═══════════════════════════════════════════════════════════
     PUBLIC API
  ═══════════════════════════════════════════════════════════ */
  window.AppearanceManager = {

    /** Save prefs to DB + cache, re-apply everything */
    async save(prefs) {
      let current = { theme: 'ocean', language: 'english' };
      try {
        const cached = sessionStorage.getItem('appearance');
        if (cached) current = JSON.parse(cached);
      } catch (_) {}

      const merged = { ...current, ...prefs };

      const res = await fetch('/api/user/appearance', {
        method:  'POST',
        headers: { 'Content-Type': 'application/json' },
        body:    JSON.stringify(merged),
      });
      const data = await res.json();

      if (data.success) {
        sessionStorage.setItem('appearance', JSON.stringify(merged));
        applyTheme(merged.theme);
        snapshotOriginals();
        walkAndTranslate(merged.language);
      }
      return data;
    },

    /** Get current prefs from cache */
    get() {
      try {
        const cached = sessionStorage.getItem('appearance');
        if (cached) return JSON.parse(cached);
      } catch (_) {}
      return { theme: 'ocean', language: 'english' };
    },

    /**
     * Extend LANG at runtime without editing this file.
     */
    addKeys(extraLang) {
      for (const [lang, keys] of Object.entries(extraLang)) {
        if (!LANG[lang]) LANG[lang] = {};
        Object.assign(LANG[lang], keys);
      }
      LOOKUP  = buildLookup();
      PHRASES = Object.keys(LOOKUP).sort((a, b) => b.length - a.length);
    },

    applyTheme,
    applyLanguage,
    snapshotOriginals,
    THEMES,
    LANG,
  };

  /* ═══════════════════════════════════════════════════════════
     BOOT
  ═══════════════════════════════════════════════════════════ */
  (function bootInstant() {
    try {
      const cached = sessionStorage.getItem('appearance');
      if (!cached) return;
      const prefs = JSON.parse(cached);
      applyTheme(prefs.theme);
      if (prefs.language && prefs.language !== 'english') {
        if (document.readyState === 'loading') {
          document.addEventListener('DOMContentLoaded', () => {
            snapshotOriginals();
            walkAndTranslate(prefs.language);
          }, { once: true });
        } else {
          snapshotOriginals();
          walkAndTranslate(prefs.language);
        }
      }
    } catch (_) {}
  })();

  function loadAndApply() {
    if (document.readyState !== 'loading') snapshotOriginals();

    fetch('/api/user/appearance')
      .then(res => res.ok ? res.json() : Promise.reject())
      .then(data => {
        const prefs = {
          theme:    data.theme    || 'ocean',
          language: data.language || 'english',
        };
        sessionStorage.setItem('appearance', JSON.stringify(prefs));
        applyTheme(prefs.theme);
        snapshotOriginals();
        walkAndTranslate(prefs.language);
        document.dispatchEvent(new CustomEvent('appearanceLoaded', { detail: prefs }));
      })
      .catch(() => {/* keep cached */});
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', loadAndApply);
  } else {
    loadAndApply();
  }

})();