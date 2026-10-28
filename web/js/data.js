/* SAMPLE DATA - only for building the UI.
   The product names, brands and specs below are made up, not real products.
   Once the backend has a gear endpoint, replace this with real data via loadGear() in gear.js. */

window.GEAR_SAMPLE = {
  racket: [
    { id: 'r1', name: 'Sample racket Falcon 01', brand: 'Brand A', price: 55, balance: 'Head light', flex: 'Flexible', weight: '5U', style: 'Doubles, counter-attack' },
    { id: 'r2', name: 'Sample racket Falcon 02', brand: 'Brand A', price: 100, balance: 'Even', flex: 'Medium', weight: '4U', style: 'All-round' },
    { id: 'r3', name: 'Sample racket Titan 10', brand: 'Brand B', price: 120, balance: 'Head heavy', flex: 'Stiff', weight: '3U', style: 'Singles, attack' },
    { id: 'r4', name: 'Sample racket Titan 20', brand: 'Brand B', price: 35, balance: 'Even', flex: 'Medium', weight: '4U', style: 'Beginner' },
    { id: 'r5', name: 'Sample racket Breeze S', brand: 'Brand C', price: 75, balance: 'Head light', flex: 'Medium', weight: '5U', style: 'Doubles, speed' },
    { id: 'r6', name: 'Sample racket Breeze X', brand: 'Brand C', price: 155, balance: 'Head heavy', flex: 'Stiff', weight: '3U', style: 'Hard attack' }
  ],
  shoe: [
    { id: 's1', name: 'Sample shoe Glide 1', brand: 'Brand A', price: 48, cushion: 'Soft', grip: 'Good grip', width: 'Wide fit', style: 'Beginner' },
    { id: 's2', name: 'Sample shoe Glide 2', brand: 'Brand A', price: 88, cushion: 'Balanced', grip: 'Excellent grip', width: 'Standard fit', style: 'Fast movement' },
    { id: 's3', name: 'Sample shoe Court Pro', brand: 'Brand B', price: 112, cushion: 'Soft', grip: 'Excellent grip', width: 'Standard fit', style: 'Frequent play, high-intensity training' },
    { id: 's4', name: 'Sample shoe Lite', brand: 'Brand C', price: 30, cushion: 'Firm', grip: 'Good grip', width: 'Narrow fit', style: 'Lightweight, recreational' }
  ],
  shuttle: [
    { id: 'c1', name: 'Sample shuttle Training', brand: 'Brand A', price: 8, material: 'Duck feather', speed: 'Speed 77', durability: 'High durability', style: 'Training' },
    { id: 'c2', name: 'Sample shuttle Match', brand: 'Brand B', price: 18, material: 'Goose feather', speed: 'Speed 77', durability: 'Medium durability', style: 'Match play' },
    { id: 'c3', name: 'Sample shuttle Club', brand: 'Brand C', price: 12, material: 'Duck feather', speed: 'Speed 76', durability: 'Medium durability', style: 'Recreational' },
    { id: 'c4', name: 'Sample plastic shuttle', brand: 'Brand C', price: 6, material: 'Plastic', speed: 'Speed 77', durability: 'Very high durability', style: 'Outdoor practice' }
  ]
};

// Filter configuration per category. type: 'check' (multi-select), 'price' (maximum price) or 'size' (EU size, shoes only).
// The 'check' options are generated automatically from the data, so adding a new product adds a new filter option.
window.GEAR_FILTERS = {
  racket: [{ key: 'brand', label: 'Brand', type: 'check' }, { key: 'level', label: 'Level', type: 'check' },
  { key: 'play', label: 'Play style', type: 'check' }, { key: 'balance', label: 'Balance point', type: 'check' },
  { key: 'flex', label: 'Shaft stiffness', type: 'check' }, { key: 'weight', label: 'Weight', type: 'check' },
  { key: 'price', label: 'Max price (€)', type: 'price' }],
  shoe: [{ key: 'brand', label: 'Brand', type: 'check' }, { key: 'gender', label: 'Gender', type: 'check' },
  { key: 'width', label: 'Fit width', type: 'check' }, { key: 'size', label: 'Your EU size', type: 'size' },
  { key: 'price', label: 'Max price (€)', type: 'price' }],
  shuttle: [{ key: 'brand', label: 'Brand', type: 'check' }, { key: 'material', label: 'Material', type: 'check' },
  { key: 'speed', label: 'Speed', type: 'check' }, { key: 'durability', label: 'Durability', type: 'check' },
  { key: 'price', label: 'Max price (per tube)', type: 'price' }]
};

// Fields shown as tags on the product card
window.GEAR_TAGS = {
  racket: ['balance', 'flex', 'weight'],
  shoe: ['gender', 'widthTag', 'sizeText', 'weightText'],
  shuttle: ['material', 'speed', 'durability']
};