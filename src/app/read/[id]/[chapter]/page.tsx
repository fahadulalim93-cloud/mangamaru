import { ReaderPage } from "@/components/reader/ReaderPage";
export const revalidate = 1800;
export default async function ReadPage({ params }: { params: Promise<{ id: string; chapter: string }> }) {
  const { id, chapter } = await params;
  const mangaId = parseInt(id, 10);
  return <ReaderPage mangaId={mangaId} chapter={chapter} />;
}
