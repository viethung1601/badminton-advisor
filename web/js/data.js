/* DỮ LIỆU MẪU - chỉ để dựng giao diện.
   Tên sản phẩm, hãng và thông số bên dưới là giả lập, không phải sản phẩm thật.
   Khi backend có endpoint gear, thay bằng dữ liệu thật qua loadGear() trong gear.js. */

window.GEAR_SAMPLE = {
  racket: [
    { id: 'r1', name: 'Vợt mẫu Falcon 01', brand: 'Hãng A', price: 1450000, balance: 'Nhẹ đầu', flex: 'Dẻo', weight: '5U', style: 'Đánh đôi, phản tạt' },
    { id: 'r2', name: 'Vợt mẫu Falcon 02', brand: 'Hãng A', price: 2650000, balance: 'Cân bằng', flex: 'Trung bình', weight: '4U', style: 'Toàn diện' },
    { id: 'r3', name: 'Vợt mẫu Titan 10', brand: 'Hãng B', price: 3200000, balance: 'Nặng đầu', flex: 'Cứng', weight: '3U', style: 'Đánh đơn, tấn công' },
    { id: 'r4', name: 'Vợt mẫu Titan 20', brand: 'Hãng B', price: 890000, balance: 'Cân bằng', flex: 'Trung bình', weight: '4U', style: 'Mới chơi' },
    { id: 'r5', name: 'Vợt mẫu Breeze S', brand: 'Hãng C', price: 1980000, balance: 'Nhẹ đầu', flex: 'Trung bình', weight: '5U', style: 'Đánh đôi, tốc độ' },
    { id: 'r6', name: 'Vợt mẫu Breeze X', brand: 'Hãng C', price: 4100000, balance: 'Nặng đầu', flex: 'Cứng', weight: '3U', style: 'Tấn công mạnh' }
  ],
  shoe: [
    { id: 's1', name: 'Giày mẫu Glide 1', brand: 'Hãng A', price: 1250000, cushion: 'Êm', grip: 'Bám tốt', width: 'Form rộng', style: 'Mới chơi' },
    { id: 's2', name: 'Giày mẫu Glide 2', brand: 'Hãng A', price: 2300000, cushion: 'Cân bằng', grip: 'Bám rất tốt', width: 'Form vừa', style: 'Di chuyển nhanh' },
    { id: 's3', name: 'Giày mẫu Court Pro', brand: 'Hãng B', price: 2950000, cushion: 'Êm', grip: 'Bám rất tốt', width: 'Form vừa', style: 'Chơi nhiều, tập cường độ cao' },
    { id: 's4', name: 'Giày mẫu Lite', brand: 'Hãng C', price: 790000, cushion: 'Cứng', grip: 'Bám tốt', width: 'Form hẹp', style: 'Nhẹ, phong trào' }
  ],
  shuttle: [
    { id: 'c1', name: 'Cầu mẫu Training', brand: 'Hãng A', price: 220000, material: 'Lông vịt', speed: 'Tốc độ 77', durability: 'Bền cao', style: 'Tập luyện' },
    { id: 'c2', name: 'Cầu mẫu Match', brand: 'Hãng B', price: 480000, material: 'Lông ngỗng', speed: 'Tốc độ 77', durability: 'Bền vừa', style: 'Thi đấu' },
    { id: 'c3', name: 'Cầu mẫu Club', brand: 'Hãng C', price: 310000, material: 'Lông vịt', speed: 'Tốc độ 76', durability: 'Bền vừa', style: 'Phong trào' },
    { id: 'c4', name: 'Cầu nhựa mẫu', brand: 'Hãng C', price: 150000, material: 'Nhựa', speed: 'Tốc độ 77', durability: 'Bền rất cao', style: 'Tập ngoài trời' }
  ]
};

// Cấu hình bộ lọc cho từng loại. type: 'check' (chọn nhiều), 'price' (giá tối đa) hoặc 'size' (size EU, chỉ giày).
// Các lựa chọn của 'check' được sinh tự động từ dữ liệu, nên thêm sản phẩm mới là có bộ lọc mới.
window.GEAR_FILTERS = {
  racket: [{ key: 'brand', label: 'Hãng', type: 'check' }, { key: 'level', label: 'Trình độ', type: 'check' },
  { key: 'play', label: 'Lối chơi', type: 'check' }, { key: 'balance', label: 'Điểm cân bằng', type: 'check' },
  { key: 'flex', label: 'Độ cứng đũa', type: 'check' }, { key: 'weight', label: 'Trọng lượng', type: 'check' },
  { key: 'price', label: 'Giá tối đa (€)', type: 'price' }],
  shoe: [{ key: 'brand', label: 'Hãng', type: 'check' }, { key: 'gender', label: 'Giới tính', type: 'check' },
  { key: 'width', label: 'Độ rộng form', type: 'check' }, { key: 'size', label: 'Size EU của bạn', type: 'size' },
  { key: 'price', label: 'Giá tối đa (€)', type: 'price' }],
  shuttle: [{ key: 'brand', label: 'Hãng', type: 'check' }, { key: 'material', label: 'Chất liệu', type: 'check' },
  { key: 'speed', label: 'Tốc độ', type: 'check' }, { key: 'durability', label: 'Độ bền', type: 'check' },
  { key: 'price', label: 'Giá tối đa (mỗi ống)', type: 'price' }]
};

// Các trường hiển thị dạng tag trên thẻ sản phẩm
window.GEAR_TAGS = {
  racket: ['balance', 'flex', 'weight'],
  shoe: ['gender', 'widthTag', 'sizeText', 'weightText'],
  shuttle: ['material', 'speed', 'durability']
};
