#include <SPI.h>

const int adc_clk_pin = 20;
const int adc_ndrdy_pin = 19;
const int spi_ncs_pin = 10;

// SPI settings
const SPISettings spi_settings(8000000, MSBFIRST, SPI_MODE1);

bool buffer_empty = true;
char adc_buffer[24];

void adc_data_ready() 
{
  // If we've sent the last set of results, grab new ones into the buffer
  if (buffer_empty)
  {
    SPI.beginTransaction(spi_settings);
    digitalWrite(spi_ncs_pin, LOW);
    SPI.transfer(adc_buffer, 24);
    digitalWrite(spi_ncs_pin, HIGH);
    SPI.endTransaction();
    buffer_empty = false;
  }
}

void setup()
{
  // Create an 8 MHz 50% duty cycle clock for the ADC
  // This requires overclocking the Teensy to 96 MHz to
  // get a 48 MHz PWM clock, which is then divided by 6
  // to get the 8 MHz clock.
  //
  // It puts us in a weird situation where the PWM counter
  // can range from 0 - 5, which doesn't nicely map to the
  // 0 - 255 range for the analogWrite() call. But the below
  // code seems to work.                
  pinMode(adc_clk_pin, OUTPUT);
  analogWriteFrequency(adc_clk_pin, 8000000);
  analogWrite(adc_clk_pin, 128);

  // Delay for a bit to make sure the ADC is alive
  delay(100);

  // Start SPI and pull !CS high
  SPI.begin();
  pinMode(spi_ncs_pin, OUTPUT);
  digitalWrite(spi_ncs_pin, HIGH);

  // Configure the ADC to use an oversampling rate of 1024,
  // and PGA gains of 64
  uint16_t clock_register = 0x3f0e;
  SPI.beginTransaction(spi_settings);
  digitalWrite(spi_ncs_pin, LOW);
  SPI.transfer16(0x6182);
  SPI.transfer(0);
  SPI.transfer16(clock_register);
  SPI.transfer(0);
  SPI.transfer16(0x6666);
  SPI.transfer(0);
  SPI.transfer16(0x0066);
  SPI.transfer(0);
  SPI.transfer16(0);
  SPI.transfer(0);
  digitalWrite(spi_ncs_pin, HIGH);
  SPI.endTransaction();

  // Wait for serial to come up
  while (!Serial);

  // Set up an interrupt on the ADC_!DRDY pin
  attachInterrupt(digitalPinToInterrupt(adc_ndrdy_pin), adc_data_ready, FALLING);
}

void loop()                     
{
  // Dump values out the serial port every time new readings come in
  if (!buffer_empty)
  {
    Serial.write(adc_buffer, 24);
    memset(adc_buffer, 0, 24);
    buffer_empty = true;
  }
}
