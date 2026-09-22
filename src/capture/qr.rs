// TimeSensei QR Code Generator & Local IP Resolver
// Matches capture/qr.py exactly.

use image::{ImageBuffer, Rgb};
use qrcode::QrCode;

pub fn get_local_ip() -> String {
    local_ip_address::local_ip()
        .map(|ip| ip.to_string())
        .unwrap_or_else(|_| "127.0.0.1".to_string())
}

pub struct QRCodeGenerator {
    pub port: u16,
    pub local_ip: String,
}

impl QRCodeGenerator {
    pub fn new(port: u16) -> Self {
        Self {
            port,
            local_ip: get_local_ip(),
        }
    }

    pub fn get_share_url(&self, photo_id: &str) -> String {
        format!("http://{}:{}/photo/{}", self.local_ip, self.port, photo_id)
    }

    pub fn generate_qr_url(&self, url: &str, size: u32) -> ImageBuffer<Rgb<u8>, Vec<u8>> {
        if let Ok(code) = QrCode::new(url.as_bytes()) {
            let qw = code.width() as u32;
            let mut out = ImageBuffer::new(size, size);
            for y in 0..size {
                let sy = ((y as f32 / size as f32) * qw as f32) as usize;
                let sy = sy.min(code.width() - 1);
                for x in 0..size {
                    let sx = ((x as f32 / size as f32) * qw as f32) as usize;
                    let sx = sx.min(code.width() - 1);
                    let is_dark = code[(sx, sy)] == qrcode::Color::Dark;
                    let col = if is_dark { Rgb([0, 0, 0]) } else { Rgb([255, 255, 255]) };
                    out.put_pixel(x, y, col);
                }
            }
            out
        } else {
            ImageBuffer::from_pixel(size, size, Rgb([255, 255, 255]))
        }
    }

    pub fn generate_qr_image(&self, photo_id: &str, size: u32) -> ImageBuffer<Rgb<u8>, Vec<u8>> {
        let url = self.get_share_url(photo_id);
        self.generate_qr_url(&url, size)
    }
}
