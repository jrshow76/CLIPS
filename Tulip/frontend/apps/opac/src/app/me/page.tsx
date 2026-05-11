import { PageHeader } from '@tulip/ui';

import { MyLibraryEmpty } from './_components/MyLibraryEmpty';

export const metadata = { title: 'MyLibrary — Tulip+ OPAC' };

export default function MyLibraryPage() {
  return (
    <div className="container-opac mx-auto max-w-[1200px] px-4 py-6 sm:px-6 lg:px-8">
      <PageHeader
        title="MyLibrary"
        description="대출 중인 자료, 예약, 연체, 회원 정보를 한 곳에서 관리합니다."
      />
      <div className="mt-6">
        <MyLibraryEmpty />
      </div>
    </div>
  );
}
