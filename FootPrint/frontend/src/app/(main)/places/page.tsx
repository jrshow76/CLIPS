import { Suspense } from 'react';
import PlaceList from '@/components/place/PlaceList';
import Loading from '@/components/common/Loading';

export default function PlacesPage() {
  return (
    <Suspense
      fallback={
        <div className="flex justify-center items-center py-20">
          <Loading size="lg" />
        </div>
      }
    >
      <PlaceList />
    </Suspense>
  );
}
