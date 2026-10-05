"""Generate bordered README previews from the firmware layouts (requires Pillow)."""
from pathlib import Path
from PIL import Image, ImageOps
from preview_start_screen import load_layout, PreviewWriter
from preview_history import PreviewHistory


def main():
    namespace = load_layout()
    output = Path(__file__).resolve().parents[1] / 'images'
    output.mkdir(exist_ok=True)

    image = Image.new('L', (264, 176), 255)
    writer = PreviewWriter(namespace, image)
    manager = namespace['ScreenManager'](writer, altitude_m=50)
    manager.screen1(22.5, 45.0, 1013.2, 1000, None, None, None,
                    co2_trend_direction=1)
    ImageOps.expand(image, border=1, fill=0).save(output / 'firmware_front.png')

    pages = (
        ('temperature', 'screen2_24h_temperature_history', 22.0, 2.0, 22.5),
        ('humidity', 'screen3_24h_humidity_history', 45.0, 10.0, 45.0),
        ('co2', 'screen4_24h_co2_history', 1000.0, 400.0, 1000.0),
        ('pressure', 'screen5_24h_pressure_history', 1013.2, 3.0, 1013.2),
    )
    for name, method, baseline, variation, current in pages:
        image = Image.new('L', (264, 176), 255)
        writer = PreviewWriter(namespace, image)
        manager = namespace['ScreenManager'](writer)
        getattr(manager, method)(current, PreviewHistory(baseline, variation))
        ImageOps.expand(image, border=1, fill=0).save(output / ('firmware_' + name + '_24h.png'))
    print('Generated five bordered firmware previews in', output)


if __name__ == '__main__':
    main()
