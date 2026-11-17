import type { Metadata } from 'next';
import './globals.css';

export const metadata: Metadata = {
  title: 'DreamsAdverstings | Premium OOH & DOOH Advertising Marketplace in Pune',
  description:
    'Discover, compare, plan, and book verified Outdoor Hoardings, Unipoles, and Digital Out-of-Home (DOOH) LED screens across Pune and India.',
  openGraph: {
    title: 'DreamsAdverstings — Make Your Brand Impossible to Ignore',
    description: 'Pune’s technology-driven OOH & DOOH advertising marketplace connecting advertisers, agencies, and verified media owners.',
    type: 'website',
    locale: 'en_IN',
  },
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body className="bg-[#F4F5F6] text-[#1F2937] antialiased selection:bg-[#D9A441] selection:text-[#101820]">
        {children}
      </body>
    </html>
  );
}
